"""Run local ordered image anchors through one persistent Hy-Nomas session.

Default is a CPU-only dry run. Use --execute on the model server explicitly.
Separate baseline/corrected runs reset the session with the same seed/settings;
identical stochastic trajectories are not guaranteed across hardware/runtime.
"""
import argparse
import hashlib
import json
import time
import uuid
import sys
import shutil
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, help='Directory containing anchors.json')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--mode', choices=['baseline', 'corrected'], default='corrected')
    parser.add_argument('--segments-per-gap', type=int, default=8)
    parser.add_argument('--strength', type=float, default=0.6)
    parser.add_argument('--output', type=Path, default=Path('/Hy-Nomas/outputs/seg_ar_demo'))
    args = parser.parse_args()
    if args.segments_per_gap < 1 or not 0 <= args.strength <= 1:
        parser.error('Invalid segment count or correction strength')
    root = args.inputs.resolve()
    meta = json.loads((root / 'anchors.json').read_text())
    anchors = meta['anchors']
    if len(anchors) < 10:
        raise ValueError('Long-route experiment requires at least 10 anchors')
    if len({a['label'] for a in anchors}) != len(anchors):
        raise ValueError('Duplicate anchor labels')
    previous = -1
    for a in anchors:
        path = (root / a['file']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Input escapes anchor directory')
        if hashlib.sha256(path.read_bytes()).hexdigest() != a['sha256']:
            raise ValueError('Anchor hash mismatch: ' + a['label'])
        if a['distance_m'] <= previous:
            raise ValueError('Anchor distances must increase')
        previous = a['distance_m']
    intervals = (len(anchors)-1)*args.segments_per_gap
    plan = {'anchors':len(anchors), 'mode':args.mode, 'segments_per_gap':args.segments_per_gap,
            'continuation_jobs':intervals+2, 'frames_per_job':49,
            'nominal_seconds_per_gap':2*args.segments_per_gap,
            'route_metres':anchors[-1]['distance_m']-anchors[0]['distance_m'],
            'correction':'last continuation segment of each gap only; existing heuristic baseline',
            'metric_motion_calibrated':False, 'tail_jobs_after_last_anchor':2}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.execute:
        return
    from PIL import Image
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, '/Hy-Nomas')
    from streetview.trajectories import build_trajectory
    session = 'long-route-' + args.mode + '-' + uuid.uuid4().hex[:12]
    dest = args.output / 'long-route-probes' / session
    dest.mkdir(parents=True)
    shutil.copytree(root, dest / 'inputs')
    frames, markers, image_ids = [], [], {}
    report = {'session':session, 'plan':plan, 'status':'running', 'jobs':[], 'visual_passed':None}
    def save():
        tmp = dest / 'report.tmp'
        tmp.write_text(json.dumps(report, indent=2))
        tmp.replace(dest / 'report.json')
        manifest = {'schema':'long-route-v1', 'frames':frames, 'anchors':markers,
                    'fps':24, 'mode':args.mode, 'report':'report.json',
                    'note':'Anchor distances are reference coordinates, not measured generated position.'}
        (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    def call(path, payload=None, raw=False):
        data = payload if raw else (json.dumps(payload).encode() if payload is not None else None)
        req = urllib.request.Request('http://127.0.0.1:18084'+path, data=data,
            headers={'Content-Type':'application/octet-stream' if raw else 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)
    def generate(name, extra, collect=True):
        prompt = json.dumps({'Style':'realistic photography', 'perspective_view':'first person',
            'subject_list':[], 'segments':[{'visual_description_long':'Travel along a downtown street with buildings, sidewalks, trees and parked vehicles.',
            'description_change':'Move steadily forward along the same street, without turning or tilting.',
            'contained_actions':[{'start_time':0,'end_time':5 if not collect else 2,'action_description':'Continue moving forward.'}]}]})
        payload = {'prompt':prompt,'num_frames':49,'segment_boundaries':[0,49],
            'trusted_segment_boundaries':True,'height':480,'width':832,'seed':43,
            'num_inference_steps':6,'session_id':session,'preserve_kv_cache':True,
            'reset_session':False,**extra}
        job = call('/v1/generate',payload)
        entry = {'name':name,'id':job['id'],'status':job['status'],
                 'conditioning':{k:payload.get(k) for k in ['reference_image_id','correction_image_id','correction_strength']}}
        report['jobs'].append(entry); save()
        started = time.monotonic()
        while job['status'] not in ['succeeded','failed','cancelled']:
            if time.monotonic()-started > 1800:
                raise TimeoutError('Job still may be running; inspect server before restarting')
            time.sleep(3)
            job = call('/v1/generate/'+job['id'])
        entry['status'] = job['status']
        entry['seconds'] = round(time.monotonic()-started, 2)
        entry['result'] = job.get('result')
        save()
        if job['status'] != 'succeeded':
            raise RuntimeError('Generation failed; inspect local server job ' + job['id'])
        if collect:
            source = args.output / 'streetview' / job['result']['id']
            manifest = json.loads((source/'manifest.json').read_text())
            observations = manifest['observations']
            if manifest['frame_stride'] != 1 or len(observations) < 49:
                raise ValueError('Dense frame export missing')
            carry = observations[:-49]
            if frames and carry:
                if len(carry) > len(frames):
                    raise ValueError('Unexpected decoder carry length')
                for filename, observation in zip(frames[-len(carry):], carry):
                    Image.open(source/observation['image']).save(dest/filename,quality=92)
            for observation in observations[-49:]:
                filename = f'frame_{len(frames):06d}.jpg'
                Image.open(source/observation['image']).save(dest/filename,quality=92)
                frames.append(filename)
        save(); print(name, 'completed', flush=True)
    try:
        for a in anchors:
            data = (root/a['file']).read_bytes()
            image_ids[a['label']] = call('/v1/reference-images?caption_mode=manual',data,True)['id']
        generate('initialize_'+anchors[0]['label'],{'reference_image_id':image_ids[anchors[0]['label']],
            'reset_session':True,'num_frames':120,'segment_boundaries':[0,120]},False)
        markers.append({'label':anchors[0]['label'],'frame_index':0,
                        'reference_distance_m':anchors[0]['distance_m'],'correction':False})
        previous_distance = anchors[0]['distance_m']
        for a in anchors[1:]:
            for part in range(args.segments_per_gap):
                correction = args.mode == 'corrected' and part == args.segments_per_gap-1
                start = previous_distance + (a['distance_m']-previous_distance)*part/args.segments_per_gap
                end = previous_distance + (a['distance_m']-previous_distance)*(part+1)/args.segments_per_gap
                camera = build_trajectory(seconds=2, fov=90)
                for i, frame in enumerate(camera['frames']):
                    frame['position']['z'] = -(start+(end-start)*i/(len(camera['frames'])-1))
                generate(f"toward_{a['label']}_{part+1}",{
                    'camera_trajectory':json.dumps(camera),'trajectory_rotation_scale':1.0,
                    'correction_image_id':image_ids[a['label']] if correction else None,
                    'correction_strength':args.strength if correction else 0})
            markers.append({'label':a['label'],'frame_index':len(frames)-1,
                            'reference_distance_m':a['distance_m'],'correction':args.mode=='corrected'})
            save()
            previous_distance = a['distance_m']
        for i in range(2):
            camera = build_trajectory(seconds=2, speed=2, fov=90)
            for frame in camera['frames']:
                frame['position']['z'] -= previous_distance + i*4
            generate(f'after_last_anchor_{i+1}',{'correction_image_id':None,'correction_strength':0,
                'camera_trajectory':json.dumps(camera),'trajectory_rotation_scale':1.0})
        report['status']='succeeded'
    except Exception as error:
        report['status']='failed'
        report['error_type']=type(error).__name__
        raise
    finally:
        save()
        print('Results:',dest,flush=True)

if __name__ == '__main__':
    main()
