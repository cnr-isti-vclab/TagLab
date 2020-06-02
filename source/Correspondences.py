from source.Blob import Blob
import numpy as np
from source.Blob import Blob
from source.Mask import intersectMask

class Correspondences(object):

    def __init__(self, img_source, img_target):

        self.source = img_source
        self.target = img_target
        self.correspondences = []
        self.dead = []
        self.born = []

        self.threshold = 0.05

    def set(self, blobs1, blobs2):
        if len(blobs1) == 0:
            for b in blobs2:
                self.born.append([b.class_name, None, b.id, 'born'])

        elif len(blobs2) == 0:
            for b in blobs1:
                self.born.append([b.class_name, b.id, None, 'dead'])

        else:
            if len(blobs1) == 1 and len(blobs2) == 1:
                status = self.status(blobs1[0], blobs2[0])
                self.correspondences.append([blobs1[0].class_name, blobs1[0].id, blobs2[0].id, status])
                return

            status = "fuse" if len(blobs1) > len(blobs2) else "split"
            for a in blobs1:
                for b in blobs2:
                    self.correspondences.append([a.class_name, a.id, b.id, status])

        print(self.correspondences)

    def autoMatch(self, blobs1, blobs2):

        for blob1 in blobs1:
            for blob2 in blobs2:
                # use bb to quickly calculate intersection
                if blob1.bbox[0] >= blob2.bbox[0] + blob2.bbox[3] or blob2.bbox[0] >= blob1.bbox[0] + blob1.bbox[3]:
                    continue
                if blob1.bbox[1] >= blob2.bbox[1] + blob2.bbox[2] or blob2.bbox[1] >= blob1.bbox[1] + blob1.bbox[2]:
                    continue

#                x1 = max(blob1.bbox[0], blob2.bbox[0])
#                y1 = max(blob1.bbox[1], blob2.bbox[1])
#                x2 = min(blob1.bbox[0] + blob1.bbox[3], blob2.bbox[0] + blob2.bbox[3])
#                y2 = min(blob1.bbox[1] + blob1.bbox[2], blob2.bbox[1] + blob2.bbox[2])
                # compute the area of intersection rectangle
#                interArea = abs(max((x2 - x1, 0)) * max((y2 - y1), 0))

                if blob2.class_name != blob1.class_name or blob1.class_name == "Empty":
                    continue

                status = self.status(blob1, blob2)
                if status != "move":
                    self.correspondences.append([blob1.class_name, blob1.id, blob2.id, status])

    def status(self, blob1, blob2):
        mask1 = Blob.getMask(blob1)
        sizeblob1 = np.count_nonzero(mask1)
        mask2 = Blob.getMask(blob2)
        sizeblob2 = np.count_nonzero(mask2)
        minblob = min(sizeblob1, sizeblob2)
        intersectionArea = np.count_nonzero(intersectMask(mask1, blob1.bbox, mask2, blob2.bbox))

        if intersectionArea <= 0.6 * minblob:
            return "move"

        elif sizeblob2 > sizeblob1 * (1.0 + self.threshold):
            return "grow"

        elif sizeblob2 < sizeblob1 * (1.0 - self.threshold):
            return "grow"

        else:
            return "same"

    def findSplit(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][1]))
        splitted = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in splitted:
                self.correspondences[i].append('split')


    def findFuse(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][2]))
        fused = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in fused:
                self.correspondences[i].append('fuse')


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
            existing.append(self.correspondences[j][1])
            missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs1[index].class_name != 'Empty':
                self.dead.append([blobs1[index].class_name, id, 'none', 'dead'])


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

            existing.append(self.correspondences[j][2])

            missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs2[index].class_name != 'Empty':
                self.born.append([blobs2[index].class_name, 'none', id, 'born'])

