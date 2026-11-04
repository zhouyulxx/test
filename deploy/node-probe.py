"""Three road nodes with complete horizontal sweeps and dense connecting edges."""
import json,math,time,sys,urllib.request
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streetview.trajectories import build_trajectory
BASE='http://127.0.0.1:18084'; OUT=Path('/Hy-Nomas/outputs/seg_ar_demo')
def call(path,data=None):
 req=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
session='node-probe-'+str(int(time.time()));dest=OUT/'route-probes'/session;dest.mkdir(parents=True)
plan=[('initial',0,0,0,0)]
for n in range(3):
 if n: plan.append(('forward_'+str(n),n-1,n,0,0))
 plan += [('left_'+str(n),n,n,0,60),('right_'+str(n),n,n,60,-60),('return_'+str(n),n,n,-60,0)]
report={'session':session,'status':'running','tests':[]};timeline=[]
def write(): (dest/'report.json').write_text(json.dumps(report,indent=2))
try:
 for k,(name,start_s,end_s,start_yaw,end_yaw) in enumerate(plan):
  camera=build_trajectory(seconds=2)
  for i,f in enumerate(camera['frames']):
   t=i/48;a=math.radians(start_yaw+(end_yaw-start_yaw)*t);f['position']['z']=-(start_s+(end_s-start_s)*t);f['quaternion']={'x':0,'y':math.sin(a/2),'z':0,'w':math.cos(a/2)}
  action=('The camera moves steadily straight forward along the center of the same street, maintaining a fixed forward heading, no sideways motion.' if start_s!=end_s else 'The camera stays at exactly the same location and rotates horizontally. No forward motion, no translation, no head tilt. The buildings and parked cars remain stationary.')
  prompt={'Style':'realistic photography','perspective_view':'first person','subject_list':[],'segments':[{'visual_description_long':'A quiet straight residential street, brick houses, sidewalks and trees, parked cars, daylight, no moving vehicles or people.','description_change':action,'contained_actions':[{'start_time':0,'end_time':2,'action_description':action}]}]}
  payload={'prompt':json.dumps(prompt),'num_frames':49,'segment_boundaries':[0,49],'trusted_segment_boundaries':True,'height':480,'width':832,'seed':43,'num_inference_steps':6,'session_id':session,'preserve_kv_cache':True,'reset_session':k==0,'camera_trajectory':json.dumps(camera),'trajectory_rotation_scale':1.0}
  start=time.monotonic();job=call('/v1/generate',payload);entry={'name':name,'job_id':job['id'],'status':job['status']};report['tests'].append(entry);write()
  while job['status'] not in ('succeeded','failed','cancelled'):
   if time.monotonic()-start>1800:raise TimeoutError('Job timeout')
   time.sleep(3);job=call('/v1/generate/'+job['id']);entry.update(status=job['status'],seconds=round(time.monotonic()-start,1));write()
  if job['status']!='succeeded':raise RuntimeError(job.get('error') or job['status'])
  result=job['result'];source=OUT/'streetview'/result['id'];m=json.loads((source/'manifest.json').read_text());obs=m['observations'];assert m['frame_stride']==1,'Dense export requires stride 1'
  previous=len(timeline)
  for f in camera['frames']:
   timeline.append({'s':-f['position']['z'],'yaw':2*math.degrees(math.atan2(f['quaternion']['y'],f['quaternion']['w'])),'kind':'route' if start_s!=end_s or name=='initial' else 'node-sweep','segment':name})
  replace=int(result.get('replace_pixel_frames',0));begin=previous-replace
  assert len(obs)==49+replace
  for o in obs:
   idx=begin+o['frame_index'];name_img=f'frame_{idx:05d}.jpg';im=Image.open(source/o['image']);im.save(dest/name_img,quality=88);timeline[idx]['image']=name_img
  entry.update(result=result,frames=len(obs));write();print(name,'succeeded',flush=True)
  manifest={'schema':'streetview-route-probe-v1','positions':'requested path units, not calibrated metres','heading_limit':60,'pitch':0,'observations':timeline,'note':'Three discrete viewing nodes. Dense edge frames do not have independent side views. Visual consistency unverified.'}
  (dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
 report['status']='succeeded'
 (OUT/'route-probes'/'nodes-latest.json').write_text(json.dumps({'manifest':f'/outputs/route-probes/{session}/manifest.json'}))
except Exception as e:report.update(status='failed',error=str(e));raise
finally:write();print(dest,flush=True)
