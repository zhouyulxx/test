"""Guarded experimental manual-image and soft continuous-correction patch."""
from pathlib import Path

def replace(s,a,b,count=1):
 assert s.count(a)==count,(a[:90],s.count(a));return s.replace(a,b)
def patch(root):
 root=Path(root)
 helper=Path(__file__).resolve().parents[1]/'streetview/anchor_correction.py'
 (root/'streetview').mkdir(exist_ok=True)
 (root/'streetview/anchor_correction.py').write_text(helper.read_text())
 p=root/'apps/seg_ar_web_server.py';s=p.read_text()
 if 'correction_image_id:' not in s:
  s=replace(s,'    reference_image_id: Optional[str] = None\n','    reference_image_id: Optional[str] = None\n    correction_image_id: Optional[str] = None\n    correction_strength: float = Field(default=0.6, ge=0.0, le=1.0)\n')
  s=replace(s,'            "reference_image_id": reference_image_id,','            "reference_image_id": reference_image_id,\n            "correction_image_id": request.correction_image_id,\n            "correction_strength": request.correction_strength,')
  s=replace(s,'            reference_latents=self._encode_reference(params),','            reference_latents=self._encode_reference(params),\n            correction_latents=self._encode_correction(params),\n            correction_strength=float(params.get("correction_strength", 0.0)),')
  marker='    def _encode_reference(self, params: Dict[str, Any]) -> Optional[torch.Tensor]:\n'
  inject='''    def _encode_correction(self, params):
        image_id = params.get("correction_image_id")
        if not image_id or not params.get("correction_strength"):
            return None
        if params.get("reference_image_id"):
            raise ValueError("Initialize first; apply correction only on moving continuations")
        cached = getattr(self, "_streetview_anchor_latents", {})
        key = (image_id, params["height"], params["width"])
        if key not in cached:
            encoded = self._encode_reference({**params, "reference_image_id": image_id, "num_frames": 120})
            cached[key] = encoded[:, :, -1:].detach().cpu()
            while len(cached) > 8:
                cached.pop(next(iter(cached)))
            self._streetview_anchor_latents = cached
        logger.info(f"Soft image correction: id={image_id}, strength={params['correction_strength']}; cache persists into continuation")
        return cached[key].to(device=self.device, dtype=torch.bfloat16)

'''
  s=replace(s,marker,inject+marker);compile(s,str(p),'exec');p.write_text(s)
 p=root/'hymm/pipeline/causal_ar.py';s=p.read_text()
 if 'correction_latents:' not in s:
  s=replace(s,'        reference_latents: Optional[torch.Tensor] = None,','        reference_latents: Optional[torch.Tensor] = None,\n        correction_latents: Optional[torch.Tensor] = None,\n        correction_strength: float = 0.0,',2)
  s=replace(s,'            reference_latents=reference_latents,','            reference_latents=reference_latents,\n            correction_latents=correction_latents,\n            correction_strength=correction_strength,')
  marker='''                        if (
                            self.cache_at_step >= 0
'''
  inject='''                        # Experimental reference correction BEFORE the next denoise pass and KV write.
                        if correction_latents is not None and correction_strength:
                            from streetview.anchor_correction import apply_anchor_correction
                            sigma = scheduler.sigmas[scheduler.step_index]
                            latents = apply_anchor_correction(latents, correction_latents, chunk_noise[:, :out_channels], sigma, correction_strength, num_inference_steps)
                            if cache_cond_latents is not None:
                                cache_cond_latents = apply_anchor_correction(cache_cond_latents, correction_latents, chunk_noise[:, :out_channels], sigma, correction_strength, num_inference_steps)

'''
  s=replace(s,marker,inject+marker);compile(s,str(p),'exec');p.write_text(s)
 p=root/'apps/seg_ar_gateway.py';s=p.read_text()
 if 'caption_mode: str = "automatic"' not in s:
  s=replace(s,'async def upload_reference_image(request: Request, background_tasks: BackgroundTasks, perspective: str = "third-person follow")','async def upload_reference_image(request: Request, background_tasks: BackgroundTasks, perspective: str = "third-person follow", caption_mode: str = "automatic")')
  s=replace(s,'        if not image_captioner.configured:\n','        if caption_mode not in ("automatic", "manual"):\n            raise HTTPException(status_code=400, detail="Unknown caption mode")\n        if caption_mode == "automatic" and not image_captioner.configured:\n')
  s=replace(s,'            image = save_reference_image(bytes(data), output_dir)\n','            image = save_reference_image(bytes(data), output_dir)\n            if caption_mode == "manual":\n                save_caption_record(image["id"], output_dir, {"caption_status": "manual"})\n                return {**image, "caption_status": "manual"}\n')
  s=replace(s,'            if not isinstance(submitted.get("pe_input"), dict) or submitted.get("reset_session") is not True:', '            if submitted.get("reset_session") is not True:')
  old='''            caption = load_caption_record(submitted["reference_image_id"], output_dir)
            if caption.get("caption_status") != "ready":
                raise HTTPException(status_code=409, detail=caption.get("caption_error") or "Image captioning is still in progress")
'''
  new='''            if isinstance(submitted.get("pe_input"), dict):
                caption = load_caption_record(submitted["reference_image_id"], output_dir)
                if caption.get("caption_status") != "ready":
                    raise HTTPException(status_code=409, detail=caption.get("caption_error") or "Image captioning is still in progress")
            else:
                try:
                    manual = json.loads(submitted.get("prompt", ""))
                    if not isinstance(manual, dict) or not manual.get("segments"):
                        raise ValueError("Missing structured segments")
                except (ValueError, TypeError):
                    raise HTTPException(status_code=400, detail="Manual image references require a structured prompt")
        if submitted.get("correction_image_id") is not None:
            try:
                resolve_reference_image(submitted["correction_image_id"], output_dir)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if not submitted.get("preserve_kv_cache") or submitted.get("reset_session") or submitted.get("reference_image_id"):
                raise HTTPException(status_code=400, detail="Correction requires a continuing persistent session")
'''
  s=replace(s,old,new);compile(s,str(p),'exec');p.write_text(s)
 s=p.read_text()
 old='            if payload.get("reference_image_id") is not None:'
 if old in s:
  s=replace(s,old,'            if payload.get("reference_image_id") is not None and pe_input is not None:')
  compile(s,str(p),'exec');p.write_text(s)
 print('Experimental soft-anchor correction installed')
if __name__=='__main__':
 import sys
 patch(sys.argv[1] if len(sys.argv)>1 else '/Hy-Nomas')
