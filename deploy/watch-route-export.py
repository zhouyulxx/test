"""Keep a live viewer checkpoint and package the completed route without model access."""
import json, time, shutil, subprocess, sys
from pathlib import Path
out=Path('/Hy-Nomas/outputs/seg_ar_demo')
for _ in range(1440):
    runs=sorted((out/'long-route-probes').glob('*/report.json'),key=lambda p:p.stat().st_mtime)
    if runs:
        dest=runs[-1].parent
        try:
            report=json.loads((dest/'report.json').read_text())
            manifest=json.loads((dest/'manifest.json').read_text())
            inputs=json.loads((dest/'inputs/anchors.json').read_text())
            if manifest['frames']:
                shutil.copy2('/opt/streetview/viewer/offline.html',dest/'index.html')
                data={'manifest':manifest,'inputs':inputs,'report':report}
                temp=dest/'data.tmp'
                temp.write_text('window.STREETVIEW_DATA = '+json.dumps(data,ensure_ascii=True)+';\n')
                temp.replace(dest/'data.js')
                (out/'long-route-viewer.html').write_text('<!doctype html><meta charset="utf-8"><title>Street route results</title><h1>Street route results</h1><p>Status: '+report['status']+'</p><p>Generated frames: '+str(len(manifest['frames']))+'</p><p><a href="long-route-probes/'+dest.name+'/index.html">Open generated viewer</a></p><p><a download href="lynchburg-offline-viewer.zip">Download completed offline viewer ZIP (available after completion)</a></p>')
            if report['status']=='succeeded':
                archive=out/'lynchburg-offline-viewer.zip'
                if not archive.exists():subprocess.run([sys.executable,'/opt/streetview/deploy/package-offline-viewer.py',str(dest),str(archive)],check=True)
                print('Packaged',archive,flush=True);break
            if report['status']=='failed':
                print('Generation failed; partial frames retained',flush=True);break
        except (FileNotFoundError,json.JSONDecodeError):pass
    time.sleep(10)
