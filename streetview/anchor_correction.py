"""Experimental soft reference correction inside flow denoising, not pixel compositing."""
def apply_anchor_correction(latents, target, noise, sigma, strength, steps, span=4, policy='legacy'):
 import torch
 if target is None or strength==0:return latents
 if not 0<=strength<=1 or steps<1:raise ValueError('Invalid correction strength/steps')
 if target.shape[:2]!=latents.shape[:2] or target.shape[-2:]!=latents.shape[-2:] or target.shape[2]!=1:raise ValueError('Anchor latent shape mismatch')
 if policy not in ('legacy','progressive'):raise ValueError('Unknown correction policy')
 if span<0:raise ValueError('Span must be nonnegative')
 n=min(span or latents.shape[2],latents.shape[2]);sigma=float(sigma)
 if not 0<=sigma<=1:raise ValueError('Sigma outside flow interpolation range')
 if policy=='progressive':
  # Correct over a complete moving segment, preserving its first latent frame.
  # This remains soft denoising guidance, not an exact endpoint replacement.
  ramp=torch.linspace(0,1,n,device=latents.device,dtype=latents.dtype).square().view(1,1,n,1,1)
  alpha=strength*(1-sigma)**2*ramp
 else:
  ramp=torch.linspace(1/n,1,n,device=latents.device,dtype=latents.dtype).square().view(1,1,n,1,1)
  alpha=(strength/steps)*(1-sigma)*ramp
 desired=(1-sigma)*target.to(latents)+sigma*noise[:,:,-n:]
 result=latents.clone();result[:,:,-n:]=torch.lerp(latents[:,:,-n:],desired,alpha)
 return result
