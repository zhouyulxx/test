"""Experimental soft reference correction inside flow denoising, not pixel compositing."""
def apply_anchor_correction(latents, target, noise, sigma, strength, steps, span=4):
 import torch
 if target is None or strength==0:return latents
 if not 0<=strength<=1 or steps<1:raise ValueError('Invalid correction strength/steps')
 if target.shape[:2]!=latents.shape[:2] or target.shape[-2:]!=latents.shape[-2:] or target.shape[2]!=1:raise ValueError('Anchor latent shape mismatch')
 n=min(span,latents.shape[2]);sigma=float(sigma)
 ramp=torch.linspace(1/n,1,n,device=latents.device,dtype=latents.dtype).square().view(1,1,n,1,1)
 alpha=(strength/steps)*(1-sigma)*ramp
 desired=(1-sigma)*target.to(latents)+sigma*noise[:,:,-n:]
 result=latents.clone();result[:,:,-n:]=torch.lerp(latents[:,:,-n:],desired,alpha)
 return result
