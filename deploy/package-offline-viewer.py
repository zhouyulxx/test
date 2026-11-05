"""Package a completed long-route run for offline viewing; no server or CDN needed."""
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
import subprocess
import html
from pathlib import Path


def safe(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or unsafe file: ' + str(name))
    return path


def package(run, output, allow_partial=False):
    run = run.resolve()
    manifest = json.loads(safe(run, 'manifest.json').read_text())
    report = json.loads(safe(run, 'report.json').read_text())
    if (report['status'] != 'succeeded' and not allow_partial) or not manifest['frames']:
        raise ValueError('Only completed, nonempty runs can be packaged')
    if report['status'] != 'succeeded':
        manifest['partial'] = True
        report['export_warning'] = 'Partial failed experiment retained for diagnosis; not a completed route.'
    for name in manifest['frames']:
        safe(run, name)
    review_path = run / 'visual-review.json'
    if review_path.is_file():
        review = json.loads(review_path.read_text())
        report['visual_passed'] = review['passed']
        report['visual_review'] = review
    inputs = json.loads(safe(run, 'inputs/anchors.json').read_text())
    for anchor in inputs['anchors']:
        path = safe(run / 'inputs', anchor['file'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != anchor['sha256']:
            raise ValueError('Input checksum mismatch')
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / 'streetview-offline'
        target.mkdir()
        names = set(manifest['frames']) | {'manifest.json', 'report.json', 'inputs/anchors.json'}
        if review_path.is_file():
            names.add('visual-review.json')
        names.update('inputs/' + a['file'] for a in inputs['anchors'])
        names.update(j['metadata_file'] for j in report['jobs'] if j.get('metadata_file'))
        for name in names:
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(safe(run, name), dest)
        (target/'report.json').write_text(json.dumps(report,indent=2))
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
            '-framerate', str(manifest['fps']), '-i', str(target/'frame_%06d.jpg'),
            '-frames:v', str(len(manifest['frames'])), '-c:v', 'libx264', '-threads', '2',
            '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(target/'route.mp4')], check=True)
        manifest['video'] = 'route.mp4'
        (target/'manifest.json').write_text(json.dumps(manifest, indent=2))
        comparisons = []
        for marker in manifest['anchors']:
            anchor = next(a for a in inputs['anchors'] if a['label'] == marker['label'])
            comparisons.append('<h2>'+html.escape(marker['label'])+' · '+str(marker['reference_distance_m'])+' m</h2><div class="pair"><figure><img src="'+html.escape(manifest['frames'][marker['frame_index']], quote=True)+'"><figcaption>生成画面</figcaption></figure><figure><img src="inputs/'+html.escape(anchor['file'], quote=True)+'"><figcaption>原始输入 anchor</figcaption></figure></div>')
        (target/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Anchor comparison</title><style>body{font:16px system-ui;background:#10151b;color:white;margin:24px}.pair{display:flex;flex-wrap:wrap}figure{margin:8px;flex:1;min-width:300px}img{width:100%}a{color:#8ac4ff}</style><h1>输入 anchor 与生成结果对照</h1><p>用于检查方向漂移和校准效果；输入点距离并非生成场景的实测距离。</p><a href="index.html">返回 viewer</a>'+''.join(comparisons))
        viewer = Path(__file__).resolve().parents[1] / 'viewer/offline.html'
        shutil.copy2(viewer, target / 'index.html')
        data = {'manifest': manifest, 'inputs': inputs, 'report': report}
        (target / 'data.js').write_text('window.STREETVIEW_DATA = ' + json.dumps(data, ensure_ascii=True) + ';\n')
        (target / 'README.txt').write_text(
            ('PARTIAL FAILED EXPERIMENT. This is not a completed or visually validated route.\n' if manifest.get('partial') else '')+
            ('VISUAL REVIEW FAILED: this completed experiment does not demonstrate stable street-following. See visual-review.json.\n' if report.get('visual_passed') is False and not manifest.get('partial') else '')+
            'Extract the entire ZIP, then open index.html in Chrome. No GPU, server, API key or internet is required.\n'
            'Controls: Space play/pause, Left/Right one frame, slider scrub, anchor buttons jump.\n'
            'route.mp4 provides smooth playback; individual frames remain available for inspection. comparison.html compares every anchor with the generated endpoint.\n'
            'Frames are AI-generated. Inputs contain Google attribution. Distances describe input locations, not calibrated generated positions.\n'
            'Anchor correction is an experimental inference heuristic; visual quality is not guaranteed.\n'
            'manifest.json, report.json, per-job JSON files and inputs/anchors.json retain settings, camera commands, cache continuity evidence, jobs and input metadata.\n'
            'Model weights and credentials are deliberately not included.\n')
        checks = {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in target.rglob('*') if p.is_file()}
        (target / 'checksums.json').write_text(json.dumps(checks, indent=2))
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for p in target.rglob('*'):
                if p.is_file():
                    z.write(p, 'streetview-offline/' + str(p.relative_to(target)))
    print(json.dumps({'archive': str(output), 'frames': len(manifest['frames']),
                      'anchors': len(inputs['anchors']), 'bytes': output.stat().st_size}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--allow-partial', action='store_true', help='Explicitly export a failed partial baseline with its failure status preserved')
    args = parser.parse_args()
    package(args.run, args.output, args.allow_partial)
