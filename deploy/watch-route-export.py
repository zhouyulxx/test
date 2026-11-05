"""Keep a live viewer checkpoint and package the completed route without model access."""
import json, time, shutil, subprocess, sys
import html
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
            if report['status']=='succeeded':
                archive=dest/'offline-viewer.zip'
                if not archive.exists():subprocess.run([sys.executable,'/opt/streetview/deploy/package-offline-viewer.py',str(dest),str(archive)],check=True)
                print('Packaged',archive,flush=True)
            completed=sum(j['status']=='succeeded' for j in report['jobs'])
            page='<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>Street route results</title><h1>连续街景生成进度</h1>'
            page+='<p>状态：'+html.escape(report['status'])+'</p><p>完成任务：'+str(completed)+' / '+str(report['plan']['continuation_jobs']+1)+'</p><p>生成帧数：'+str(len(manifest['frames']))+'</p>'
            if manifest['frames']:
                page+='<p><a href="long-route-probes/'+dest.name+'/index.html">打开当前生成的 viewer</a>（生成期间可刷新查看新增片段）</p>'
            if report['status']=='succeeded':
                page+='<p><a download href="long-route-probes/'+dest.name+'/offline-viewer.zip">下载完整离线 viewer ZIP</a></p>'
            (out/'long-route-viewer.html').write_text(page)
            if report['status']=='succeeded':break
            if report['status']=='failed':
                print('Generation failed; partial frames retained',flush=True);break
        except (FileNotFoundError,json.JSONDecodeError):pass
    time.sleep(10)
