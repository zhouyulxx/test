"""Real A/B/C image inputs: A-init baseline vs same-state soft B/C correction."""
import json,time,sys,urllib.request,shutil,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,'/Hy-Nomas')
from streetview.trajectories import build_trajectory
from streetview.anchor_correction import apply_anchor_correction
BASE='http://127.0.0.1:18084';OUT=Path('/Hy-Nomas/outputs/seg_ar_demo')
def call(path,data=None,raw=False):
 body=data if raw else (None if data is None else json.dumps(data).encode())
 req=urllib.request.Request(BASE+path,data=body,headers={'Content-Type':'application/octet-stream' if raw else 'application/json'})
 with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
def wait(job,path):
 start=time.monotonic()
 while job['status'] not in ('succeeded','failed','cancelled'):
  if time.monotonic()-start>1200:raise TimeoutError('Job timeout')
  time.sleep(3);job=call(path+job['id'])
 if job['status']!='succeeded':raise RuntimeError(job.get('error',job['status']))
 return job
session='three-anchor-'+str(int(time.time()));dest=OUT/'anchor-probes'/session
report={'session':session,'status':'running','jobs':[],'method':'soft latent correction during denoising; no hard endpoint replacement','visual_quality_passed':None}
if len(sys.argv)>1:
 dest=Path(sys.argv[1]);report=json.loads((dest/'report.json').read_text());session=report['session']
 if call('/v1/sessions/'+session+'/status')['status']!='active':raise RuntimeError('Cannot resume an expired model state')
 if report.get('rollbacks') or any(j['name'].startswith('corrected') for j in report['jobs']):raise RuntimeError('Resume is only supported before correction begins; inspect cache state first')
 report['status']='running';report.pop('error',None)
else:dest.mkdir(parents=True)
def save():(dest/'report.json').write_text(json.dumps(report,indent=2))
def prompt(seconds):
 return json.dumps({'Style':'realistic photography','perspective_view':'first person','subject_list':[],'segments':[{'visual_description_long':'A paved outdoor campus walkway beside brick buildings, trees and pedestrians, daylight. Keep the same buildings and path.','description_change':'The camera moves straight forward along the path without turning or tilting.','contained_actions':[{'start_time':0,'end_time':seconds,'action_description':'Move steadily forward along the same path.'}]}]})
def generate(name,extra):
 for old in report['jobs']:
  if old['name']==name and old['status']=='succeeded':
   print(name,'reusing completed result',flush=True);return old['result']
 payload={'prompt':prompt(5 if name=='initial_A' else 2),'num_frames':49,'segment_boundaries':[0,49],'trusted_segment_boundaries':True,'height':480,'width':832,'seed':43,'num_inference_steps':6,'session_id':session,'preserve_kv_cache':True,'reset_session':False,**extra}
 start=time.monotonic();job=call('/v1/generate',payload);entry={'name':name,'id':job['id'],'status':'running','conditioning':{k:payload.get(k) for k in ['reference_image_id','correction_image_id','correction_strength']}};report['jobs'].append(entry);save()
 job=wait(job,'/v1/generate/');entry.update(status='succeeded',seconds=round(time.monotonic()-start,1),result=job['result']);save();print(name,'succeeded',flush=True);return job['result']
def rollback():
 job=call('/v1/sessions/'+session+'/rollback',{});job=wait(job,'/v1/sessions/'+session+'/rollback/');report.setdefault('rollbacks',[]).append(job['result']);save()
def camera(a,b):
 c=build_trajectory(seconds=2)
 for i,f in enumerate(c['frames']):f['position']['z']=-(a+(b-a)*i/48)
 return json.dumps(c)
def collect(result,prefix,previous=None):
 source=OUT/'streetview'/result['id'];m=json.loads((source/'manifest.json').read_text());assert m['frame_stride']==1
 carry=m['observations'][:-49]
 if previous and carry:
  assert len(carry)<=len(previous)
  for name,o in zip(previous[-len(carry):],carry):Image.open(source/o['image']).save(dest/name,quality=92)
 obs=m['observations'][-49:];assert len(obs)==49
 images=[]
 for i,o in enumerate(obs):
  name=f'{prefix}_{i:03d}.jpg';Image.open(source/o['image']).save(dest/name,quality=92);images.append(name)
 return images
def score(name,target):
 from hymm.utils.image_resize import fit_image_to_frame
 a=np.asarray(Image.open(dest/name).convert('RGB'),dtype=float);b=np.asarray(fit_image_to_frame(Image.open(dest/target).convert('RGB'),(832,480)),dtype=float)
 return {'rgb_mae':round(float(np.abs(a-b).mean()),3),'upper_half_rgb_mae':round(float(np.abs(a[:240]-b[:240]).mean()),3)}
try:
 import torch
 x=torch.zeros(1,32,13,2,2);b=torch.ones(1,32,1,2,2)
 assert torch.equal(apply_anchor_correction(x,b,x,0,0,6),x)
 y=apply_anchor_correction(x,b,x,0,.6,6);assert torch.equal(y[:,:,:-4],x[:,:,:-4]) and 0<float(y[:,:,-1].mean())<1
 assert torch.equal(apply_anchor_correction(x,b,x,1,.6,6),x)
 report['correction_math_checks']='passed'
 meta=json.loads(Path('/opt/streetview/anchor-inputs/anchors.json').read_text());report['inputs']=meta;ids=dict(report.get('image_ids',{}))
 for a in meta['anchors']:
  label=a['label']
  if label in ids:continue
  data=urllib.request.urlopen(a['url'],timeout=120).read();(dest/(label+'.jpg')).write_bytes(data)
  ids[label]=call('/v1/reference-images?caption_mode=manual',data,raw=True)['id']
 report['image_ids']=ids;save()
 generate('initial_A',{'reference_image_id':ids['A'],'reset_session':True,'num_frames':120,'segment_boundaries':[0,120]})
 d1,d2=meta['distances_metres'];frames={};metrics={}
 for mode,strength in [('baseline',0),('corrected',.6)]:
  if mode=='corrected':rollback();rollback()
  frames[mode]=[];metrics[mode]={}
  for label,a,b in [('B',0,d1),('C',d1,d1+d2)]:
   result=generate(mode+'_toward_'+label,{'camera_trajectory':camera(a,b),'trajectory_rotation_scale':1.0,'correction_image_id':ids[label] if strength else None,'correction_strength':strength})
   imgs=collect(result,mode+'_'+label,frames[mode]);frames[mode]+=imgs;metrics[mode][label]=score(imgs[-1],label+'.jpg')
  metrics[mode]['B']=score(frames[mode][48],'B.jpg')
 report.update(status='succeeded',metrics=metrics,limitations=['Campus pedestrian path, not Google Street View panoramas','Moving pedestrians confound pixel metrics','Requested translation uses recorded distance but model displacement is not calibrated','Soft latent correction is an untrained inference heuristic; geometry unverified'])
 (dest/'manifest.json').write_text(json.dumps({'schema':'three-anchor-probe-v1','frames':frames,'anchors':['A.jpg','B.jpg','C.jpg'],'report':'report.json','fps':24,'note':report['method']}))
 (OUT/'anchor-probes'/'latest.json').write_text(json.dumps({'manifest':f'/outputs/anchor-probes/{session}/manifest.json'}))
 print(json.dumps({'session':session,'status':'succeeded','metrics':metrics}),flush=True)
except Exception as e:report.update(status='failed',error=str(e));raise
finally:save();print(dest,flush=True)
