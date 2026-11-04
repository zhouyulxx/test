"""Validate independent branch coverage without claiming visual geometry."""
import json,time
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
root=Path('/Hy-Nomas/outputs/seg_ar_demo/route-probes');p=max(root.glob('branch-probe-*'));deadline=time.monotonic()+1800
while time.monotonic()<deadline:
 r=json.loads((p/'report.json').read_text())
 if r['status']!='running':break
 time.sleep(5)
if r['status']!='succeeded':raise RuntimeError(r.get('error',r['status']))
m=json.loads((p/'manifest.json').read_text());obs=m['observations'];assert len(obs)==441
assert all((p/o['image']).is_file() for o in obs)
restores=[x['rollback']['status'] for x in r['tests'] if 'rollback' in x];assert restores==['succeeded']*6
remaining=[x['rollback']['result']['remaining_segments'] for x in r['tests'] if 'rollback' in x];assert remaining==[1,1,2,2,3,3],remaining
checks=[]
for n in range(3):
 views=[o for o in obs if o['s']==n and o['kind']=='node-sweep'];assert len(views)==98
 assert min(o['yaw'] for o in views)<-59.99 and max(o['yaw'] for o in views)>59.99
 anchor=next(o for o in reversed(obs) if o['segment']==('initial' if n==0 else 'forward_'+str(n)))
 a=Image.open(p/anchor['image']).convert('RGB');diffs={}
 for side in ['left','right']:
  b=next(o for o in obs if o['segment']==side+'_'+str(n));im=Image.open(p/b['image']).convert('RGB')
  diffs[side]=round(sum(ImageStat.Stat(ImageChops.difference(a,im)).mean)/3,3)
 checks.append({'node':n,'side_frames':98,'zero_heading_branch_start_rgb_mae':diffs})
result={'status':'passed','observations':441,'successful_state_restores':6,'remaining_segments_after_restore':remaining,'nodes':checks,'geometric_consistency_passed':None,'note':'Cached center view repeats exactly by design; this is not proof of multiview geometry.'}
(p/'coverage-check.json').write_text(json.dumps(result,indent=2));print(p.name,json.dumps(result),flush=True)
