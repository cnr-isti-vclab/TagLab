import numpy as np
from skimage import measure

"""
Convert points to indices and swaps x, and y.
"""
def pointsToIndices(points):
    points = np.swapaxes(points, 0, 1).astype(int)
    points[[0, 1],:] = points[[1, 0],:]

"""
compute the bounding box of a set of points in format [[x0, y0], [x1, y1]... ]
padding is used, since when painting we draw a 'fat' line
"""
def pointsBox(points, pad = 0):
    box = [points[:, 1].min()-pad,
           points[:, 0].min()-pad,
           points[:, 0].max() + pad,
           points[:, 1].max() + pad]
    box[2] -= box[1]
    box[3] -= box[0]
    return np.array(box).astype(int)

def jointBox(boxes):
    box = boxes[0]
    for b in boxes:
        box = np.array([
            min(box[0], b[0]),
            min(box[1], b[1]),
            max(box[1] + box[2], b[1] + b[2]),
            max(box[0] + box[3], b[0] + b[3])
        ])
        box[2] -= box[1]
        box[3] -= box[0]
    return box.astype(int)

"""
returns (mask, bbox) where bbox is the union and mask is set to 0
"""
def jointMask(box0, box1):
    box = jointBox([box0, box1])
    mask = np.zeros((box[3], box[2])).astype(np.uint8)
    return (mask, box)


"""
set the mask values to 'value' where the points (translated by bbox left,top) 
"""
def paintPoints(mask, box, points, value):
    h = mask.shape[0]
    w = mask.shape[1]
    points = points - [box[1], box[0]]
    points = np.swapaxes(points, 0, 1).astype(int)

    points = points[:, (points[1] > 0) & (points[0] > 0) & (points[1] < h - 1) & (points[0] < w - 1)]
    index = points[1,] * w + points[0,]


    np.put(mask, index, value, 'clip')
#    for x in range(-1, 2):
#        for y in range(-1, 2):
#            np.put(mask, index + y*w + x, value, 'clip')



"""
paints the foreground of the mask as 'value' on the mask. dmask is the destination larger and contains smask
"""
def paintMask(dmask, dbox, smask, sbox, value):
    # range is [minx, miny, maxx, maxy], absolute ranges
    drange = [dbox[0], dbox[1], dbox[0] + dbox[3], dbox[1] + dbox[2]]
    srange = [sbox[0], sbox[1], sbox[0] + sbox[3], sbox[1] + sbox[2]]

    #intersection
    range = [ max(drange[0], srange[0]), max(drange[1], srange[1]), min(drange[2], srange[2]),  min(drange[3], srange[3])]

    #compute local ranges
    d = dmask[range[0] - dbox[0]:range[2] - dbox[0], range[1] - dbox[1]:range[3] - dbox[1]]
    s = smask[range[0] - sbox[0]:range[2] - sbox[0], range[1] - sbox[1]:range[3] - sbox[1]]

    if value == 0:
        d[:] = d & ~s
    else:
        d[:] = d | s


"""
Merge two masks.
"""
def union(maskA, boxA, maskB, boxB):

    (mask, box) = jointMask(boxA, boxB)
    paintMask(mask, box, maskA, boxA, 1)
    paintMask(mask, box, maskB, boxB, 1)

    #regions = measure.regionprops(measure.label(mask))
    return (mask, box)

"""
Subtracts the second mask from the first mask
"""
def subtract(maskA, boxA, maskB, boxB):

    (mask, box) = jointMask(boxA, boxB)
    paintMask(mask, box, maskA, boxA, 1)
    paintMask(mask, box, maskB, boxB, 0)

    regions = measure.regionprops(measure.label(mask))
    return (mask, box)
