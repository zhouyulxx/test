"""Package a completed long-route run for offline viewing; no server or CDN needed."""
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


def safe(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or unsafe file: ' + str(name))
    return path


def package(run, output):
    run = run.resolve()
    manifest = json.loads(safe(run, 'manifest.json').read_text())
    report = json.loads(safe(run, 'report.json').read_text())
    if report['status'] != 'succeeded' or not manifest['frames']:
        raise ValueError('Only completed, nonempty runs can be packaged')
    for name in manifest['frames']:
        safe(run, name)
    inputs = json.loads(safe(run, 'inputs/anchors.json').read_text())
    for anchor in inputs['anchors']:
        path = safe(run / 'inputs', anchor['file'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != anchor['sha256']:
            raise ValueError('Input checksum mismatch')
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / 'streetview-offline'
        target.mkdir()
        names = set(manifest['frames']) | {'manifest.json', 'report.json', 'inputs/anchors.json'}
        names.update('inputs/' + a['file'] for a in inputs['anchors'])
        for name in names:
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(safe(run, name), dest)
        viewer = Path(__file__).resolve().parents[1] / 'viewer/offline.html'
        shutil.copy2(viewer, target / 'index.html')
        data = {'manifest': manifest, 'inputs': inputs, 'report': report}
        (target / 'data.js').write_text('window.STREETVIEW_DATA = ' + json.dumps(data, ensure_ascii=True) + ';\n')
        (target / 'README.txt').write_text(
            'Extract the entire ZIP, then open index.html in Chrome. No GPU, server, API key or internet is required.\n'
            'Controls: Space play/pause, Left/Right one frame, slider scrub, anchor buttons jump.\n'
            'Frames are AI-generated. Inputs contain Google attribution. Distances describe input locations, not calibrated generated positions.\n'
            'Anchor correction is an experimental inference heuristic; visual quality is not guaranteed.\n'
            'manifest.json, report.json and inputs/anchors.json retain settings, jobs and input metadata.\n'
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
    args = parser.parse_args()
    package(args.run, args.output)
