"""Run with the model runtime's torch installation."""
import unittest
import torch
from streetview.anchor_correction import apply_anchor_correction
class CorrectionTest(unittest.TestCase):
 def setUp(self):
  self.x=torch.zeros(1,32,13,2,2);self.target=torch.ones(1,32,1,2,2)
 def test_disabled_is_identity(self):
  self.assertTrue(torch.equal(apply_anchor_correction(self.x,self.target,self.x,0,0,6),self.x))
 def test_soft_and_localized(self):
  y=apply_anchor_correction(self.x,self.target,self.x,0,.6,6)
  self.assertTrue(torch.equal(y[:,:,:-4],self.x[:,:,:-4]));self.assertGreater(float(y[:,:,-1].mean()),0);self.assertLess(float(y[:,:,-1].mean()),1)
 def test_no_correction_at_pure_noise(self):
  self.assertTrue(torch.equal(apply_anchor_correction(self.x,self.target,self.x,1,.6,6),self.x))
 def test_shape_validation(self):
  with self.assertRaises(ValueError):apply_anchor_correction(self.x,torch.ones(1,32,2,2,2),self.x,0,.6,6)
if __name__=='__main__':unittest.main()
