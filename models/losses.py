from typing import Any, Callable, Iterable, List, Set, Tuple, TypeVar, Union
import torch
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch import einsum
from torch import Tensor
from scipy.ndimage import distance_transform_edt as distance


###############################################################################
# SURFACE LOSS - ORIGINAL IMPLEMENTATION

# def uniq(a: Tensor) -> Set:
#     return set(torch.unique(a.cpu()).numpy())
#
# def sset(a: Tensor, sub: Iterable) -> bool:
#     return uniq(a).issubset(sub)
#
# def simplex(t: Tensor, axis=1) -> bool:
#     _sum = t.sum(axis).type(torch.float32)
#     _ones = torch.ones_like(_sum, dtype=torch.float32)
#     return torch.allclose(_sum, _ones)
#
#
# def one_hot(t: Tensor, axis=1) -> bool:
#     return simplex(t, axis) and sset(t, [0, 1])
#
#
# def class2one_hot(seg: Tensor, C: int) -> Tensor:
#
#     b, w, h = seg.shape  # type: Tuple[int, int, int]
#
#     res = torch.stack([seg == c for c in range(C)], dim=1).type(torch.int32)
#     assert res.shape == (b, C, w, h)
#     assert one_hot(res)
#
#     return res
#
# def one_hot2dist(seg: np.ndarray) -> np.ndarray:
#     assert one_hot(torch.Tensor(seg), axis=0)
#     C: int = len(seg)
#
#     res = np.zeros_like(seg)
#     for c in range(C):
#         posmask = seg[c].astype(np.bool)
#
#         if posmask.any():
#             negmask = ~posmask
#             res[c] = distance(negmask) * negmask - (distance(posmask) - 1) * posmask
#
#     return res
#
#
# class SurfaceLoss():
#
#     def __init__(self, **kwargs):
#         # Self.idc is used to filter out some classes of the target mask. Use fancy indexing
#         self.idc: List[int] = kwargs["idc"]
#         print(f"Initialized {self.__class__.__name__} with {kwargs}")
#
#     def __call__(self, probs: Tensor, dist_maps: Tensor, _: Tensor) -> Tensor:
#         assert simplex(probs)
#         assert not one_hot(dist_maps)
#
#         pc = probs[:, self.idc, ...].type(torch.float32)
#         dc = dist_maps[:, self.idc, ...].type(torch.float32)
#
#         multipled = einsum("bcwh,bcwh->bcwh", probs, dist_maps)
#
#         loss = multipled.mean()
#
#         return loss
#

###############################################################################
# SURFACE LOSS

def one_hot2dist(seg):

    n_classes = seg.shape[1]

    posmask = seg[:, 1:n_classes, :, :]  # BACKGROUND is skipped (!)
    posmask = posmask.astype(np.bool)
    res = np.zeros_like(posmask)

    if posmask.any():
        negmask = ~posmask
        res = distance(negmask) * negmask - (distance(posmask) - 1) * posmask

    return res

def surface_loss(y_true, y_pred):

    n_classes = y_pred.shape[1]

    y_pred_prob = torch.softmax(y_pred, axis=1)

    N = y_true.shape[0]

    loss = 0.0
    for i in range(N):

        y_true_onehot = make_one_hot(y_true, n_classes)
        y_true_onehot_numpy = y_true_onehot.cpu().numpy()
        dist_maps = one_hot2dist(y_true_onehot_numpy)  # it works on a numpy array
        dist_maps_tensor = torch.from_numpy(dist_maps).to(torch.float32)
        dist_maps_tensor = dist_maps_tensor.to(device='cuda:0')
        #dist_maps_tensor = Variable(dist_maps_tensor)

        loss += dist_maps_tensor * y_pred_prob[i]

    return loss.mean()


###############################################################################
# DICE LOSS

def make_one_hot(labels, C=2):

    one_hot = torch.FloatTensor(labels.size(0), C, labels.size(1), labels.size(2)).zero_()
    one_hot = one_hot.to('cuda:0')
    target = one_hot.scatter_(1, labels.unsqueeze(1), 1.0)

    target = Variable(target)

    return target


def dice_loss(input, target):

    """

    :param input: input is a torch variable of size Batch x nclasses x H x W representing log probabilities for each class
    :param target:  target is a 1-hot representation of the groundtruth, shoud have same size as the input
    :return: Dice loss

    """

    # input: torch.Tensor,
    # target: torch.Tensor) -> torch.Tensor:

    input = torch.softmax(input, axis=1)

    target_onehot = make_one_hot(target)

    smooth = 1.0

    input = input.view(-1)
    target_onehot = target_onehot.view(-1)

    intersection = (input * target_onehot).sum()

    L = 1.0 - ((2.0 * intersection) + smooth) / (input.sum() + target_onehot.sum() + smooth)

    return L


# class DiceLoss(nn.Module):
#
#
#
#     def __init__(self) -> None:
#         super(DiceLoss, self).__init__()
#         self.eps: float = 1e-6
#
#     def forward(  # type: ignore
#             self,
#             input: torch.Tensor,
#             target: torch.Tensor) -> torch.Tensor:
#
#             y_pred = 1. / (1. + torch.exp(-input))
#
#             y_pred = y_pred.to(dtype=torch.float64)
#
#             numerator = 2 * (target * y_pred).sum()
#             denominator = (target + y_pred).sum()
#
#             return 1 - numerator / (denominator + 1e-6)
#
#
