from source.Blob import Blob
import numpy as np
from source.Blob import Blob
from source.Mask import intersectMask
import pandas as pd


class Correspondences(object):

    def __init__(self, img_source, img_target):

        self.source = img_source
        self.target = img_target
        self.correspondences = []
        self.dead = []
        self.born = []
        self.data = pd.DataFrame(data = None, columns=['Blob 1', 'Blob 2', 'Area1', 'Area2', 'Class', 'Action','Split\Fuse'])

    def save(self):
        data = { "source": self.source, "target": self.target, "correspondences": self.data.to_json }

    def autoMatch(self, blobs1, blobs2):

        for blob1 in blobs1:
            for blob2 in blobs2:
                # use bb to quickly calculate intersection
                # if (blob1.class_name == 'Pocillopora'):
                x1 = max(blob1.bbox[0], blob2.bbox[0])
                y1 = max(blob1.bbox[1], blob2.bbox[1])
                x2 = min(blob1.bbox[0] + blob1.bbox[3], blob2.bbox[0] + blob2.bbox[3])
                y2 = min(blob1.bbox[1] + blob1.bbox[2], blob2.bbox[1] + blob2.bbox[2])
                # compute the area of intersection rectangle
                interArea = abs(max((x2 - x1, 0)) * max((y2 - y1), 0))

                # if interArea != 0 and blob2.class_name == blob1.class_name:
                if interArea != 0 and blob2.class_name == blob1.class_name and blob1.class_name != 'Empty':
                    # this is the get mask function for the outer contours, I put it here using two different if conditions so getMask just runs just on intersections
                    mask1 = Blob.getMask(blob1)
                    sizeblob1 = np.count_nonzero(mask1)
                    mask2 = Blob.getMask(blob2)
                    sizeblob2 = np.count_nonzero(mask2)
                    minblob = min(sizeblob1, sizeblob2)
                    intersectionArea = np.count_nonzero(intersectMask(mask1, blob1.bbox, mask2, blob2.bbox))

                    if (intersectionArea > (0.6 * minblob)) and (sizeblob2 > sizeblob1 + sizeblob1 * 0.05):
                        self.correspondences.append([blob1.id, blob2.id, sizeblob1, sizeblob2, blob1.class_name, 'grow', 'none'])

                    elif (intersectionArea > (0.6 * minblob)) and (sizeblob2 < sizeblob1 - sizeblob1 * 0.05):
                        self.correspondences.append([blob1.id, blob2.id, sizeblob1, sizeblob2, blob1.class_name, 'shrink', 'none'])

                    elif (intersectionArea > (0.6 * minblob)) and (
                            int(sizeblob2) in range(int(sizeblob1 - sizeblob1 * 0.05),
                                                    int(sizeblob1 + sizeblob1 * 0.05))):
                        self.correspondences.append([blob1.id, blob2.id, sizeblob1, sizeblob2, blob1.class_name, 'same', 'none'])


    def findSplit(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][1]))
        splitted = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in splitted:
                self.correspondences[i][6] = 'split'



    def findFuse(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][2]))
        fused = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in fused:
                self.correspondences[i][6 ] = 'fuse'



    def findDead(self, blobs1):

        # """
        # Deads are all the blobs that are in project 1 but don't match with any blobs of project 2
        # """
        all_blobs = []
        existing = []
        missing = []

        for i in range(0, len(blobs1)):
            all_blobs.append(blobs1[i].id)

        for j in range(0, len(self.correspondences)):
            existing.append(int(self.correspondences[j][1]))
            missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs1[index].class_name != 'Empty':
                self.dead.append([id, None,  blobs1[index].area, 0.0, blobs1[index].class_name, 'dead', 'none'])


    def findBorn(self, blobs2):

        # """
        # Borns are all the blobs that are in project 2 but don't match with any blobs of project 1
        # MAYBE NOW MOVED MIGHT BE EXCHANGED FOR NEW BORN
        # """

        all_blobs = []
        existing = []
        missing = []

        for i in range(0, len(blobs2)):
            all_blobs.append(blobs2[i].id)

        for j in range(0, len(self.correspondences)):
            existing.append(int(self.correspondences[j][2]))
            missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs2[index].class_name != 'Empty':
                self.born.append([None, id, 0.0, blobs2[index].area, blobs2[index].class_name, 'born', 'none'])