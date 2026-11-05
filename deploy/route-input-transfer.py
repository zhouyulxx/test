"""Add a validated route ZIP import behind the existing authenticated proxy."""
from pathlib import Path
import io, json, zipfile, hashlib, uuid, shutil


def install(app, output_dir):
    from fastapi import Request, HTTPException
    from fastapi.responses import HTMLResponse
    @app.get('/streetview-import', response_class=HTMLResponse)
    def page():
        return '''<!doctype html><meta charset="utf-8"><title>Street route import</title><h1>Street route ZIP import</h1><p>Import original anchor images and metadata for the long-route experiment.</p><input id="file" type="file" accept=".zip"><button id="upload">Import ZIP</button><pre id="status"></pre><script>document.getElementById('upload').onclick=async()=>{const f=document.getElementById('file').files[0];if(!f)return;const s=document.getElementById('status');s.textContent='Uploading…';try{const r=await fetch('./v1/streetview-route-inputs',{method:'POST',body:f});s.textContent=await r.text();}catch(e){s.textContent=String(e);}};</script>'''
    @app.post('/v1/streetview-route-inputs')
    async def upload(request: Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>20*1024*1024:raise HTTPException(413,'ZIP exceeds20MB')
        try:
            z=zipfile.ZipFile(io.BytesIO(raw))
            if sum(i.file_size for i in z.infolist())>40*1024*1024:raise ValueError('Expanded ZIP too large')
            metadata_names=[n for n in z.namelist() if n.endswith('anchors.json')]
            if len(metadata_names)!=1:raise ValueError('Expected one anchors.json')
            meta_name=metadata_names[0];prefix=meta_name[:-len('anchors.json')]
            meta=json.loads(z.read(meta_name));anchors=meta['anchors']
            if not 10<=len(anchors)<=100:raise ValueError('Expected10..100anchors')
            files={}
            from PIL import Image
            for a in anchors:
                p=Path(a['file'])
                if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe image path')
                b=z.read(prefix+a['file'])
                if hashlib.sha256(b).hexdigest()!=a['sha256']:raise ValueError('Checksum mismatch')
                with Image.open(io.BytesIO(b)) as im:im.verify()
                files[a['file']]=b
            dest=Path(output_dir)/'route-inputs'/uuid.uuid4().hex
            dest.mkdir(parents=True)
            for name,b in files.items():
                p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
            (dest/'anchors.json').write_text(json.dumps(meta,indent=2))
            (Path(output_dir)/'route-inputs/latest.json').write_text(json.dumps({'directory':str(dest)}))
            return {'status':'verified','anchors':len(anchors),'directory':str(dest)}
        except (ValueError,KeyError,zipfile.BadZipFile,OSError) as e:
            raise HTTPException(400,str(e))


if __name__=='__main__':
    import psutil, subprocess, sys, time
    root=Path('/Hy-Nomas');target=root/'apps/seg_ar_gateway.py'
    shutil.copy2(__file__,root/'apps/streetview_route_transfer.py')
    s=target.read_text()
    needle='    app.mount("/outputs", StaticFiles(directory=str(output_dir)), name="outputs")'
    if 'from apps.streetview_route_transfer import install' not in s:
        if needle not in s:raise RuntimeError('Gateway patch location missing')
        s=s.replace(needle,'    from apps.streetview_route_transfer import install\n    install(app, output_dir)\n'+needle)
        compile(s,str(target),'exec');target.write_text(s)
    matches=[]
    for p in psutil.process_iter(['pid','cmdline']):
        cmd=p.info['cmdline'] or []
        if any(x.endswith('seg_ar_gateway.py') or x=='apps.seg_ar_gateway' for x in cmd):matches.append(p)
    if len(matches)!=1:raise RuntimeError('Expected one gateway process')
    p=matches[0];cmd=p.cmdline();env=p.environ();cwd=p.cwd()
    p.terminate();p.wait(timeout=20)
    with open(root/'.runtime/seg_ar_demo/gateway.log','ab') as log:
        child=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
    (root/'.runtime/seg_ar_demo/gateway.pid').write_text(str(child.pid))
    print('Gateway import installed; model worker preserved')
