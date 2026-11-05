"""Exercise refresh request ordering and decoder carry boundaries without a GPU."""
import hashlib, importlib.util, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

spec=importlib.util.spec_from_file_location('probe',Path(__file__).resolve().parents[1]/'deploy/long-route-probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class RefreshTest(unittest.TestCase):
 def test_refresh_rebuilds_state_without_overwriting_bridge(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);inputs=root/'inputs';inputs.mkdir();out=root/'out';out.mkdir();anchors=[];requests=[]
   for i in range(10):
    name=f'{i}.jpg';Image.new('RGB',(16,16),(i*10,0,0)).save(inputs/name)
    anchors.append({'label':f'P{i+1:02}','file':name,'distance_m':i*40,'sha256':hashlib.sha256((inputs/name).read_bytes()).hexdigest()})
   (inputs/'anchors.json').write_text(json.dumps({'anchors':anchors}))
   def urlopen(req,timeout=None):
    if '/reference-images?' in req.full_url:return io.BytesIO(b'{"id":"image"}')
    body=json.loads(req.data);requests.append(body);n=len(requests);name=f'job{n}';source=out/'streetview'/name;source.mkdir(parents=True)
    Image.new('RGB',(16,16),(n*10,0,0)).save(source/'new.jpg')
    Image.new('RGB',(16,16),(0,255,0)).save(source/'carry.jpg')
    (source/'manifest.json').write_text(json.dumps({'frame_stride':1,'observations':[{'image':'carry.jpg'}]+[{'image':'new.jpg'}]*49}))
    (out/(name+'.json')).write_text(json.dumps({'continue_kv_cache':not body['reset_session']}))
    return io.BytesIO(json.dumps({'id':name,'status':'succeeded','result':{'id':name,'metadata_url':'/outputs/'+name+'.json'}}).encode())
   argv=['probe',str(inputs),'--execute','--output',str(out),'--diagnostic-anchors','2','--anchor-state-refresh','reference','--strength','1']
   with patch.object(sys,'argv',argv),patch('urllib.request.urlopen',urlopen):probe.main()
   run=next((out/'long-route-probes').iterdir());report=json.loads((run/'report.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
   self.assertEqual(len(requests),8);self.assertEqual(len(manifest['frames']),294)
   self.assertEqual([i for i,r in enumerate(requests) if r['reset_session']],[0,5])
   self.assertEqual(requests[5]['reference_image_id'],'image');self.assertEqual(requests[5]['num_frames'],120)
   self.assertTrue(report['jobs'][6]['decoder_carry_skipped']);self.assertFalse(report['jobs'][7]['decoder_carry_skipped'])
   self.assertFalse(report['plan']['uninterrupted_cache']);self.assertEqual(report['plan']['total_jobs'],8)
   self.assertEqual(len(json.loads((run/'inputs/anchors.json').read_text())['anchors']),2)
   pixel=Image.open(run/'frame_000195.jpg').getpixel((0,0));self.assertGreater(pixel[0],40);self.assertLess(pixel[1],10)

if __name__=='__main__':unittest.main()
