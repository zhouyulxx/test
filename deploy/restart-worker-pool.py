"""Restart the managed GPU pool, never a worker child that its parent will respawn.

Run only after stopping generation submissions. Active inference is interrupted.
Gateway, authentication, model files and completed outputs are preserved.
"""
import argparse
import subprocess
from pathlib import Path
import psutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--history', choices=['recent', 'temporal_context'], default='recent')
    parser.add_argument('--frame-stride', type=int, default=1)
    args = parser.parse_args()
    if args.frame_stride < 1:
        parser.error('Frame stride must be positive')
    pools = []
    for process in psutil.process_iter(['cmdline']):
        command = process.info['cmdline'] or []
        if any(Path(token).name == 'run_seg_ar_gpu_pool.sh' for token in command):
            pools.append(process)
    if len(pools) != 1:
        raise RuntimeError(f'Expected exactly one managed pool; found {len(pools)}')
    pool = pools[0]
    children = pool.children(recursive=True)
    print({'pool': pool.pid, 'child_count': len(children), 'history': args.history,
           'frame_stride': args.frame_stride, 'execute': args.execute}, flush=True)
    if not args.execute:
        return
    command = [arg for arg in pool.cmdline()
               if not arg.startswith('inference.sliding_window.sampling=')]
    command.append('inference.sliding_window.sampling=' + args.history)
    environment = pool.environ()
    environment['STREETVIEW_FRAME_STRIDE'] = str(args.frame_stride)
    cwd = pool.cwd()
    runtime = Path(environment.get('RUNTIME_DIR', str(Path(cwd)/'.runtime/seg_ar_demo')))
    # Stop respawning before touching children. Do not start a second worker
    # alongside the original supervisor, which can lose the persistent session.
    pool.suspend()
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children, timeout=10)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=10)
    if alive:
        pool.resume()
        raise RuntimeError('Old worker children did not exit; refusing duplicate startup')
    pool.kill()
    pool.wait(timeout=10)
    with (runtime/'pool-restart.log').open('ab') as log:
        restarted = subprocess.Popen(command, cwd=cwd, env=environment,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    (runtime/'gpu_pool.pid').write_text(str(restarted.pid))
    print('Managed pool restarted:', restarted.pid, flush=True)


if __name__ == '__main__':
    main()
