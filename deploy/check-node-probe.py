"""Check completed node dataset coverage and produce same-pose comparisons."""
import json,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops,ImageStat
root=Path('/Hy-Nomas/outputs/seg_ar_demo/route-probes')
p=max(root.glob('node-probe-*'));deadline=time.monotonic()+1800
while time.monotonic()<deadline:
 r=json.loads((p/'report.json').read_text())
 if r['status']!='running':break
 time.sleep(5)
if r['status']!='succeeded':raise RuntimeError(r)
m=json.loads((p/'manifest.json').read_text());obs=m['observations'];checks=[];sheet=Image.new('RGB',(832,3*265),'#101827');draw=ImageDraw.Draw(sheet)
for n in range(3):
 views=[o for o in obs if o['s']==n and o['kind']=='node-sweep']
 assert min(o['yaw'] for o in views)<=-59.99 and max(o['yaw'] for o in views)>=59.99
 anchor=next(o for o in reversed(obs) if o['segment']==('initial' if n==0 else 'forward_'+str(n)))
 returned=next(o for o in reversed(obs) if o['segment']=='return_'+str(n))
 a=Image.open(p/anchor['image']).convert('RGB');b=Image.open(p/returned['image']).convert('RGB')
 mae=sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
 checks.append({'node':n,'side_frames':len(views),'min_yaw':min(o['yaw'] for o in views),'max_yaw':max(o['yaw'] for o in views),'anchor':anchor['image'],'returned':returned['image'],'same_pose_rgb_mae':round(mae,3),'visual_consistency':'requires human inspection; MAE is not geometric proof'})
 sheet.paste(a.resize((416,240)),(0,n*265));sheet.paste(b.resize((416,240)),(416,n*265));draw.text((8,n*265+243),f'Node {n}: BEFORE turn | AFTER returning to same pose, MAE {mae:.2f}',fill='white')
sheet.save(p/'node-loop-check.jpg',quality=92)
(p/'coverage-check.json').write_text(json.dumps({'nodes':checks,'observations':len(obs),'coverage_passed':True,'geometric_consistency_passed':None},indent=2))
print(p,'COVERAGE PASS; visual consistency unverified',flush=True)
