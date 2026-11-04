from pathlib import Path
import json
import tempfile
import unittest

import numpy as np
from PIL import Image

from streetview.export import export_observations
from streetview.trajectories import build_trajectory


class ExportTest(unittest.TestCase):
    def test_no_pose_does_not_make_up_pose(self):
        with tempfile.TemporaryDirectory() as d:
            arr = np.zeros((13, 16, 32, 3), dtype=np.uint8)
            f = export_observations(arr, {"request_id": "a/b", "num_frames": 13}, Path(d), 24)
            doc = json.loads(f.read_text())
            self.assertEqual(len(doc["observations"]), 4)
            self.assertIsNone(doc["observations"][0]["camera_pose_input"])
            self.assertEqual(doc["observations"][0]["pose_alignment"], "unavailable")
            with Image.open(f.parent / "frame_00000.png") as image:
                self.assertEqual(image.size, (32, 16))

    def test_pose_mismatch_unverified(self):
        traj = build_trajectory(seconds=2)
        self.assertEqual((len(traj["frames"]) - 1) % 4, 0)
        with tempfile.TemporaryDirectory() as d:
            arr = np.zeros((45, 8, 8, 3), dtype=np.uint8)
            f = export_observations(arr, {"request_id": "b", "num_frames": 49,
                "camera_trajectory": json.dumps(traj)}, Path(d), 24)
            doc = json.loads(f.read_text())
            self.assertIsNone(doc["observations"][0]["camera_pose_input"])
            self.assertEqual(doc["observations"][0]["pose_alignment"], "unverified_decoder_tail_or_hidden_frames")

    def test_catalog_preserves_previous_runs(self):
        with tempfile.TemporaryDirectory() as d:
            arr = np.zeros((5, 8, 8, 3), dtype=np.uint8)
            for run in ['first', 'second', 'second']:
                export_observations(arr, {"request_id": run, "num_frames": 5}, Path(d), 24)
            index = json.loads((Path(d) / 'streetview/index.json').read_text())
            self.assertEqual([r['request_id'] for r in index['runs']], ['second', 'first'])
            for run in index['runs']:
                self.assertTrue((Path(d) / 'streetview' / run['manifest']).is_file())

    def test_streaming_replacement_tail(self):
        trajectory = build_trajectory(seconds=2, yaw_degrees=45)
        with tempfile.TemporaryDirectory() as d:
            arr = np.zeros((57, 8, 8, 3), dtype=np.uint8)
            path = export_observations(arr, {"request_id": "tail", "num_frames": 49,
                "camera_trajectory": trajectory}, Path(d), 24,
                decoder_metadata={"replace_pixel_frames": 8})
            doc = json.loads(path.read_text())
            self.assertEqual(doc['observations'][0]['pose_alignment'], 'previous_segment_replacement_tail')
            self.assertIsNone(doc['observations'][0]['camera_pose_input'])
            self.assertEqual(doc['observations'][2]['camera_pose_input'], trajectory['frames'][0])
            self.assertIn('decoder_verified', doc['observations'][2]['pose_alignment'])

    def test_pose_exact_index(self):
        traj = build_trajectory(seconds=2)
        with tempfile.TemporaryDirectory() as d:
            arr = np.zeros((49, 8, 8, 3), dtype=np.uint8)
            f = export_observations(arr, {"request_id": "c", "num_frames": 49,
                "camera_trajectory": traj}, Path(d), 24)
            doc = json.loads(f.read_text())
            self.assertEqual(doc["observations"][0]["pose_alignment"], "input_pose_exact_index")
            self.assertIsNotNone(doc["observations"][0]["camera_pose_input"])


if __name__ == '__main__':
    unittest.main()
