"""Exercise the actual MP4/archive export contract with tiny image fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from PIL import Image

spec=importlib.util.spec_from_file_location('offline_package',Path(__file__).resolve().parents[1]/'deploy/package-offline-viewer.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'run'
        (self.root/'inputs').mkdir(parents=True)
        Image.new('RGB',(64,36),'red').save(self.root/'inputs/anchor.jpg')
        frames=[]
        for i in range(3):
            name=f'frame_{i:06d}.jpg';frames.append(name)
            Image.new('RGB',(64,36),(i*80,50,100)).save(self.root/name)
        self.write('inputs/anchors.json',{'anchors':[{'label':'P01','file':'anchor.jpg','sha256':hashlib.sha256((self.root/'inputs/anchor.jpg').read_bytes()).hexdigest()}]})
        self.manifest={'frames':frames,'fps':24,'anchors':[{'label':'P01','frame_index':0,'reference_distance_m':0}]}
        self.write('manifest.json',self.manifest)
        self.write('generation.json',{'continue_kv_cache':True})
        self.report={'status':'succeeded','jobs':[{'metadata_file':'generation.json'}]}
        self.write('report.json',self.report)
        self.output=Path(self.temp.name)/'viewer.zip'

    def write(self,name,value):
        (self.root/name).write_text(json.dumps(value))

    def test_video_metadata_and_checksums_survive_export(self):
        module.package(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            read=lambda name:archive.read('streetview-offline/'+name)
            self.assertEqual(json.loads(read('manifest.json'))['video'],'route.mp4')
            self.assertGreater(len(read('route.mp4')),1000)
            self.assertTrue(json.loads(read('generation.json'))['continue_kv_cache'])
            self.assertIn(b'frame_000000.jpg',read('comparison.html'))
            for name,digest in json.loads(read('checksums.json')).items():
                self.assertEqual(hashlib.sha256(read(name)).hexdigest(),digest)

    def test_failed_run_requires_explicit_partial_export(self):
        self.report.update(status='failed',visual_passed=False)
        self.write('report.json',self.report)
        with self.assertRaises(ValueError):module.package(self.root,self.output)
        module.package(self.root,self.output,allow_partial=True)
        with zipfile.ZipFile(self.output) as archive:
            manifest=json.loads(archive.read('streetview-offline/manifest.json'))
            report=json.loads(archive.read('streetview-offline/report.json'))
            self.assertTrue(manifest['partial'])
            self.assertEqual(report['status'],'failed')
            self.assertFalse(report['visual_passed'])
            self.assertIn('export_warning',report)

    def test_frame_path_cannot_escape_run(self):
        (self.root.parent/'outside.jpg').write_bytes(b'private test fixture')
        self.manifest['frames']=['../outside.jpg'];self.write('manifest.json',self.manifest)
        with self.assertRaises(ValueError):module.package(self.root,self.output)


if __name__=='__main__':unittest.main()
