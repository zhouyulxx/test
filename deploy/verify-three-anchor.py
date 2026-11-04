"""Verify actual submitted image conditions and exported data, not visual quality."""
import json,sys,hashlib,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,'/Hy-Nomas')
from hymm.utils.image_resize import fit_image_to_frame
p=Path(sys.argv[1]);r=json.loads((p/'report.json').read_text());assert r['status']=='succeeded';assert len(r['jobs'])==5
conditions=[]
for entry in r['jobs']:
 with urllib.request.urlopen('http://127.0.0.1:18084/v1/generate/'+entry['id'],timeout=30) as f:j=json.load(f)
 assert j['status']=='succeeded';payload=json.loads(Path('/Hy-Nomas/.runtime/seg_ar_demo/jobs.json').read_text())['jobs'][entry['id']]['payload'];conditions.append({'name':entry['name'],**{k:payload.get(k) for k in ['reference_image_id','correction_image_id','correction_strength','reset_session','preserve_kv_cache']}})
assert conditions[0]['reference_image_id']==r['image_ids']['A']
assert conditions[3]['correction_image_id']==r['image_ids']['B'] and conditions[4]['correction_image_id']==r['image_ids']['C']
assert all(c['reset_session'] is False and c['preserve_kv_cache'] is True for c in conditions[1:])
assert [x['remaining_segments'] for x in r['rollbacks']]==[2,1]
m=json.loads((p/'manifest.json').read_text());assert all(len(v)==98 for v in m['frames'].values());assert all((p/f).is_file() for v in m['frames'].values() for f in v)
diffs={}
for label,index in [('B',48),('C',97)]:
 a=np.asarray(Image.open(p/m['frames']['baseline'][index]),dtype=float);b=np.asarray(Image.open(p/m['frames']['corrected'][index]),dtype=float);diffs[label]=round(float(np.abs(a-b).mean()),3)
 assert diffs[label]>0
source=Path('/Hy-Nomas/outputs/seg_ar_demo/streetview')/r['jobs'][0]['result']['id'];im=json.loads((source/'manifest.json').read_text());decoded=np.asarray(Image.open(source/im['observations'][-1]['image']).convert('RGB'),dtype=float);target=np.asarray(fit_image_to_frame(Image.open(p/'A.jpg').convert('RGB'),(832,480)),dtype=float)
v={'status':'passed','image_conditions':conditions,'input_sha256':{k:hashlib.sha256((p/(k+'.jpg')).read_bytes()).hexdigest() for k in 'ABC'},'generated_frames':196,'initial_A_reconstruction_rgb_mae':round(float(np.abs(decoded-target).mean()),3),'baseline_vs_corrected_endpoint_rgb_mae':diffs,'metrics':r['metrics'],'visual_quality_passed':None}
(p/'verification.json').write_text(json.dumps(v,indent=2));print(json.dumps(v),flush=True)
