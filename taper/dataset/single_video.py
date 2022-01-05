from pathlib import Path
import pickle
import json5
from torch.utils.data import Dataset


class SingleVideo(Dataset):
    """
    Load vibe params by video name. (mp4 video not required)
    Return continuous vibe params and corresponding gesture labels of shape: 8*4 + 1
    Should not be shuffled
    If dense_indices are provided, only selected params are returned
    """
    def __init__(self, vibe_path: Path,
                 gesture_label_path: Path,
                 dense_indices: list = None):
        with vibe_path.open('rb') as f:
            self.vibe = pickle.load(f)
        with gesture_label_path.open('r') as f:
            self.gesture = json5.load(f)
        # Note that 'vibe' is shorter than 'gesture' due to failed tracks caused by image occlusion.
        # Therefore, the 'frame' in 'vibe' is used as index for 'gesture'
        self.dense_indices = dense_indices

    def __len__(self):
        return len(self.vibe)

    def __getitem__(self, index):
        vibe_params = self.vibe[index]  # vibe params for 1 frame
        vibe_params = vibe_params.get(1)  # person "1"
        frame_num = vibe_params['frame_ids'][0]  # frame_num is 0-based
        gesture = self.gesture[frame_num]

        tensor_VC = self._to_gcn_feature(vibe_params)
        if self.dense_indices is not None:
            tensor_VC = tensor_VC[self.dense_indices]

        return {'tensor_vc': tensor_VC,  # the batch_size in this dataset is the num_frames, or 'T'
                'label': gesture,  # a scalar
                }

    def _to_gcn_feature(self, vibe_params):
        """
        Convert vibe_params to STGCN input features of shape C,V.
        STGCN requires input features of shape N,C,T,V. (N:batch, C: num_features. T: num_frames. V: num_keypoints)
        :param vibe_params:
        :return:
        """
        pose = vibe_params['pose']  # pose params of shape 72,
        pose_VC = pose.reshape((-1, 3))  # (num_keypoints, rotation_3d)
        # pose_VC_2 = pose_VC[part_indices, :]  # Only take useful parts, do not send unused parts into GCN.
        return pose_VC