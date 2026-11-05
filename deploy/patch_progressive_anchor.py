"""Expose explicit progressive soft correction while retaining the legacy policy."""
from pathlib import Path
import shutil


def change(source, old, new, count=1):
    if source.count(old) != count:
        raise RuntimeError('Unexpected progressive patch location: '+old[:100])
    return source.replace(old,new)


def patch(root):
    root=Path(root)
    helper=Path(__file__).resolve().parents[1]/'streetview/anchor_correction.py'
    shutil.copy2(helper,root/'streetview/anchor_correction.py')
    path=root/'apps/seg_ar_web_server.py';source=path.read_text()
    if 'correction_policy: str' not in source:
        source=change(source,'    correction_strength: float = Field(default=0.6, ge=0.0, le=1.0)',
            '    correction_strength: float = Field(default=0.6, ge=0.0, le=1.0)\n    correction_policy: str = "legacy"\n    correction_span: int = Field(default=4, ge=0)')
        source=change(source,'            "correction_strength": request.correction_strength,',
            '            "correction_strength": request.correction_strength,\n            "correction_policy": request.correction_policy,\n            "correction_span": request.correction_span,')
        source=change(source,'            correction_strength=float(params.get("correction_strength", 0.0)),',
            '            correction_strength=float(params.get("correction_strength", 0.0)),\n            correction_policy=params.get("correction_policy", "legacy"),\n            correction_span=int(params.get("correction_span", 4)),')
        compile(source,str(path),'exec');path.write_text(source)
    path=root/'hymm/pipeline/causal_ar.py';source=path.read_text()
    if 'correction_policy: str' not in source:
        source=change(source,'        correction_strength: float = 0.0,',
            '        correction_strength: float = 0.0,\n        correction_policy: str = "legacy",\n        correction_span: int = 4,',2)
        source=change(source,'            correction_strength=correction_strength,',
            '            correction_strength=correction_strength,\n            correction_policy=correction_policy,\n            correction_span=correction_span,')
        source=change(source,'sigma, correction_strength, num_inference_steps)',
            'sigma, correction_strength, num_inference_steps, span=correction_span, policy=correction_policy)',2)
        compile(source,str(path),'exec');path.write_text(source)
    print('Progressive soft-anchor policy installed; legacy policy retained')


if __name__=='__main__':
    import sys
    patch(sys.argv[1] if len(sys.argv)>1 else '/Hy-Nomas')
