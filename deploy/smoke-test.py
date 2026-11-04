#!/usr/bin/env python3
"""Exercise the local authenticated-deployment backend without exposing credentials.

Run inside the Pod. Writes a report and contact sheet beneath the existing
protected outputs directory. This tests generation/export, not scene accuracy.
"""
import argparse
import json
import math
import time
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streetview.trajectories import build_trajectory


def call(base, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:18084')
    parser.add_argument('--output', default='/Hy-Nomas/outputs/seg_ar_demo')
    parser.add_argument('--timeout', type=int, default=2400)
    args = parser.parse_args()
    output = Path(args.output)
    session = 'streetview-smoke-' + str(int(time.time()))
    report_dir = output / 'streetview-tests' / session
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {'session': session, 'tests': [], 'status': 'running',
              'scope': 'Real generation/export smoke test; no claim of geometric consistency.'}
    write = lambda: (report_dir / 'report.json').write_text(json.dumps(report, indent=2))
    write()
    all_observations = []
    try:
        health = call(args.base, '/health')
        if not health.get('worker_online') or health.get('busy'):
            raise RuntimeError('Worker must be online and idle: ' + str(health))
        yaw = 0
        for name, delta_yaw, speed in [('initial', 0, 0), ('left45', 45, 0),
                                      ('return_forward', -45, 0), ('forward', 0, 1)]:
            camera = build_trajectory(seconds=2, yaw_degrees=delta_yaw, speed=speed)
            for frame in camera['frames']:
                local_yaw = 2 * math.atan2(frame['quaternion']['y'], frame['quaternion']['w'])
                angle = local_yaw + math.radians(yaw)
                frame['quaternion'] = {'x': 0, 'y': math.sin(angle/2), 'z': 0, 'w': math.cos(angle/2)}
            payload = {'prompt': 'First-person eye-level view along a quiet residential street in daylight, brick houses on both sides, trees, parked cars, realistic photography, no people.',
                'num_frames': 49, 'segment_boundaries': [0,49], 'trusted_segment_boundaries': True,
                'height': 480, 'width': 832, 'seed': 42, 'num_inference_steps': 6,
                'session_id': session, 'preserve_kv_cache': True, 'reset_session': name == 'initial',
                'camera_trajectory': json.dumps(camera)}
            payload['prompt'] = json.dumps({'Style': 'realistic photography', 'perspective_view': 'first person', 'subject_list': [], 'segments': [{'visual_description_long': payload['prompt'], 'description_change': payload['prompt'], 'contained_actions': [{'start_time': 0, 'end_time': 2, 'action_description': 'Camera observes the residential street.'}]}]})
            started = time.monotonic()
            job = call(args.base, '/v1/generate', payload)
            entry = {'name': name, 'job_id': job['id'], 'status': job['status']}
            report['tests'].append(entry)
            write()
            print(json.dumps(entry), flush=True)
            while job['status'] not in ('succeeded', 'failed', 'cancelled'):
                if time.monotonic() - started > args.timeout:
                    raise TimeoutError('Generation timed out; inspect job before retry')
                time.sleep(5)
                job = call(args.base, '/v1/generate/' + job['id'])
                entry.update(status=job['status'], elapsed_seconds=round(time.monotonic()-started,1))
                write()
            if job['status'] != 'succeeded':
                entry['error'] = job.get('error')
                raise RuntimeError(job.get('error') or job['status'])
            entry['result'] = job['result']
            manifest_path = output / 'streetview' / job['result']['id'] / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            entry['manifest'] = str(manifest_path.relative_to(output))
            entry['exported_observations'] = len(manifest['observations'])
            for obs in manifest['observations']:
                if obs.get('camera_pose_input') is not None:
                    item = dict(obs)
                    item['image'] = '../../' + str((manifest_path.parent / obs['image']).relative_to(output))
                    item['source_test'] = name
                    all_observations.append(item)
            entry['aligned_observations'] = sum(o.get('camera_pose_input') is not None for o in manifest['observations'])
            yaw += delta_yaw
            print(json.dumps(entry), flush=True)
            write()
        atlas = {'schema': 'nomas-streetview-session-atlas-v1', 'session_id': session,
                 'observations': all_observations, 'note': 'Requested poses; visual consistency unverified.'}
        (report_dir / 'manifest.json').write_text(json.dumps(atlas, indent=2))
        from PIL import Image, ImageDraw
        sheet = Image.new('RGB', (832, len(report['tests'])*260), '#101827')
        draw = ImageDraw.Draw(sheet)
        for row, test in enumerate(report['tests']):
            source = output / test['manifest']
            doc = json.loads(source.read_text())
            items = doc['observations']
            for col, obs in enumerate([items[0], items[-1]]):
                with Image.open(source.parent / obs['image']) as im:
                    im.thumbnail((416,240))
                    sheet.paste(im, (col*416,row*260+20))
            draw.text((10,row*260+3), test['name'] + ' | first / last exported frames',fill='white')
        sheet.save(report_dir/'contact-sheet.jpg',quality=90)
        report['status'] = 'succeeded'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        raise
    finally:
        write()
        print('Report: '+str(report_dir/'report.json'),flush=True)

if __name__ == '__main__':
    main()
