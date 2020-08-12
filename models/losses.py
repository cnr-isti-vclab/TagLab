import torch
from torch.autograd import Variable
import numpy as np
from scipy.ndimage import distance_transform_edt as distance
from math import tanh

###############################################################################
# SURFACE LOSS

def one_hot2dist(seg):
    """
    Given a NCLASSES x HEIGHT x WIDTH segmentation matrix it returns the corresponding distance map per-classes.
    """

    C = seg.shape[0]
    res = np.zeros_like(seg)
    for c in range(1, C):  # background is excluded (C=0)
        posmask = seg[c].astype(np.bool)
        if posmask.any():
            negmask = ~posmask
            res[c] = distance(negmask) * negmask - (distance(posmask) - 1) * posmask

    return res



def surface_loss_fake(y_true, n_classes):

    N = y_true.shape[0]

    y_true_onehot = make_one_hot(y_true, n_classes)
    y_true_onehot_numpy = y_true_onehot.cpu().numpy()

    loss = 0.0
    for i in range(N):

        dist_maps = one_hot2dist(y_true_onehot_numpy[i])  # it works on a numpy array
        dist_maps_tensor = torch.from_numpy(dist_maps).to(torch.float32)
        dist_maps_tensor = dist_maps_tensor.to(device='cuda:0')
        loss += dist_maps_tensor * y_true_onehot[i]

    return loss.mean()


def surface_loss(y_true, y_pred):

    n_classes = y_pred.shape[1]

    y_pred_prob = torch.softmax(y_pred, axis=1)

    N = y_true.shape[0]

    y_true_onehot = make_one_hot(y_true, n_classes)
    y_true_onehot_numpy = y_true_onehot.cpu().numpy()

    loss = 0.0
    for i in range(N):

        dist_maps = one_hot2dist(y_true_onehot_numpy[i])  # it works on a numpy array
        dist_maps_tensor = torch.from_numpy(dist_maps).to(torch.float32)
        dist_maps_tensor = dist_maps_tensor.to(device='cuda:0')
        #dist_maps_tensor = Variable(dist_maps_tensor)

        loss += dist_maps_tensor * y_pred_prob[i]

    xmin = torch.tensor(-90.0)
    xmax = torch.tensor(90.0)

    return (loss.mean() - xmin) / (xmax - xmin)        # our corrections
    #return loss.mean()               # original boundary loss


###############################################################################
# DICE LOSS

def make_one_hot(labels, C=2):

    one_hot = torch.FloatTensor(labels.size(0), C, labels.size(1), labels.size(2)).zero_()
    one_hot = one_hot.to('cuda:0')
    target = one_hot.scatter_(1, labels.unsqueeze(1), 1.0)

    target = Variable(target)

    return target


# def dice_loss(input, target):
#
#     """
#
#     :param input: input is a torch variable of size Batch x nclasses x H x W representing log probabilities for each class
#     :param target:  target is a 1-hot representation of the groundtruth, shoud have same size as the input
#     :return: Dice loss
#
#     """
#
#     # input: torch.Tensor,
#     # target: torch.Tensor -> torch.Tensor
#
#
#     nclasses = input.shape[1]
#
#     input = torch.softmax(input, axis=1)
#     target_onehot = make_one_hot(target, nclasses)
#
#     # exclude Background (assumed = 0)
#     input_no_back = input[:, 1:, ...]
#     target_onehot_no_back = target_onehot[:, 1:, ...]
#
#     #input_no_back = input_no_back.view(-1)
#     #target_onehot_no_back = target_onehot_no_back.view(-1)
#
#     smooth = 1.0
#     intersection = (input_no_back * target_onehot_no_back).sum()
#     L = 1.0 - ((2.0 * intersection) + smooth) / (input_no_back.sum() + target_onehot_no_back.sum() + smooth)
#
#     return L


def GDL(input, target, weights):

    """
    Generalized Dice Loss

    :param input: input is a torch variable of size Batch x nclasses x H x W representing the predictions for each class
    :param target:  target is a 1-hot representation of the groundtruth, shoud have same size as the input
    :return: Generalized dice loss

    """

    nclasses = input.shape[1]

    input = torch.softmax(input, axis=1)
    target_onehot = make_one_hot(target, nclasses)

    # exclude Background (assumed = 0)
    input_no_back = input[:, 1:, ...]
    target_onehot_no_back = target_onehot[:, 1:, ...]

    intersection = weights[0] * (input_no_back[:, 0, :, :] * target_onehot_no_back[:, 0, :, :]).sum()
    union = weights[0] * (input_no_back[:, 0, :, :].sum() + target_onehot_no_back[:, 0, :, :].sum())

    # nclasses-1 because we have excluded the background with the previous assignment
    # (input_no_back = .. , target_onehot_no_back = ..)
    for j in range(1, nclasses-1):
        intersection += weights[j] * (input_no_back[:, j, :, :] * target_onehot_no_back[:, j, :, :]).sum()
        union += weights[j] * (input_no_back[:, j, :, :].sum() + target_onehot_no_back[:, j, :, :].sum())

    smooth = 1.0
    L = 1.0 - ((2.0 * intersection) + smooth) / (union + smooth)

    return L



######################################################################################################
# TVERSKY


def tversky(input, target, alpha, beta):
    """
    Tversky loss

    :param input: input is a torch variable of size Batch x nclasses x H x W representing the predictions for each class
    :param target: target is a 1-hot representation of the groundtruth, shoud have same size as the input
    :return: Generalized dice loss

    Notes:
        alpha = beta = 0.5 => dice coeff
        alpha = beta = 1 => tanimoto coeff
        alpha + beta = 1 => F beta coeff

    References:
        https://arxiv.org/abs/1706.05721
    """

    nclasses = input.shape[1]

    probs = torch.softmax(input, axis=1)
    target_onehot = make_one_hot(target, nclasses)

    #probs = probs.view(-1)
    #target_onehot = target_onehot.view(-1)

    smooth = 1.0

    dims = (0,2,3)
    TP = torch.sum(probs * target_onehot, dims)
    FN = torch.sum(target_onehot * (1.0 - probs), dims)
    FP = torch.sum((1 - target_onehot) * probs, dims)

    TR = ((TP + smooth) / (TP + alpha * FN + beta * FP + smooth)).mean()

    return TR



def focal_tversky(input, target, alpha, beta, gamma):
    """
    Focal Tversky loss (combine focal loss to fight imbalance with Tversky loss

    :param input: input is a torch variable of size Batch x nclasses x H x W representing the predictions for each class
    :param target: target is a 1-hot representation of the groundtruth, shoud have same size as the input
    :return: Generalized dice loss

    Notes:
        alpha = beta = 0.5 => dice coeff
        alpha = beta = 1 => tanimoto coeff
        alpha + beta = 1 => F beta coeff

    References:
        https://arxiv.org/abs/1706.05721
    """

    nclasses = input.shape[1]

    probs = torch.softmax(input, axis=1)
    target_onehot = make_one_hot(target, nclasses)

    #probs = probs.view(-1)
    #target_onehot = target_onehot.view(-1)

    smooth = 1.0

    dims = (0,2,3)
    TP = torch.sum(probs * target_onehot, dims)
    FN = torch.sum(target_onehot * (1.0 - probs), dims)
    FP = torch.sum((1 - target_onehot) * probs, dims)

    TR = ((TP + smooth) / (TP + alpha * FN + beta * FP + smooth))

    TR = 1.0 - TR
    TR = TR.pow(gamma)
    FTR = TR.sum()

    return FTR
