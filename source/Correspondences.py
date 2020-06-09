from source.Blob import Blob
import numpy as np
from source.Blob import Blob
from source.Mask import intersectMask
import pandas as pd


class Correspondences(object):

    def __init__(self, img_source, img_target, correspondences = None):

        self.source = img_source
        self.target = img_target
        self.correspondences = []
        self.dead = []
        self.born = []
        self.threshold = 1.05
        self.data = pd.DataFrame(data = correspondences, columns=['Blob 1', 'Blob 2', 'Area1', 'Area2', 'Class', 'Action', 'Split\Fuse'])

    def save(self):
        return { "source": self.source.id, "target": self.target.id, "correspondences": self.data.values.tolist() }

    def set(self, sourceblobs, targetblobs):

        #assumes one oth the two list has 1 blob only.
        type = ""
        action = "none"
        if len(sourceblobs) == 0:
            action = "born"

        elif len(targetblobs) == 0:
            action = "gone"

        elif len(sourceblobs) > 1:
            action = "join"
        elif len(targetblobs) > 1:
            action = "split"
        elif sourceblobs[0].area > targetblobs[0].area*self.threshold:
            type = "shrink"
        elif sourceblobs[0].area < targetblobs[0].area/self.threshold:
            type = "grow"
        else:
            type = "same"
            #TODO consider morph!

        #orphaned nodes: not in sourceblob, but had some connections in  targetblobs (dead now) and viceversa
        #they will become born or dead
        targetorphaned = self.data[self.data['Blob 1'].isin([b.id for b in sourceblobs])]['Blob 2']
        sourceorphaned = self.data[self.data['Blob 2'].isin([b.id for b in targetblobs])]['Blob 1']

        targetorphaned = list(set(targetorphaned) - set([b.id for b in targetblobs]))
        sourceorphaned = list(set(sourceorphaned) - set([b.id for b in sourceblobs]))

#        print("Sourceblobs: ", [b.id for b in sourceblobs])
#        print("Targetblobs: ", [b.id for b in targetblobs])
#        print("Orphaned source: ", sourceorphaned)
#        print("Orphaned target: ", targetorphaned)

        #remove all correspondences where orphaned
        self.data = self.data[self.data['Blob 1'].isin([b.id for b in sourceblobs]) == False]
        self.data = self.data[self.data['Blob 2'].isin([b.id for b in targetblobs]) == False]

#        print("Clean data: ", self.data)
        for id in targetorphaned:
            if id is None: #bordn and dead result in orfaned  None
                continue
            target = self.target.annotations.blobById(id)
            row = [None, target.id, 0.0, target.area, target.class_name, "", "born"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data.append(df)

        for id in sourceorphaned:
            if id is None:
                continue
            source = self.source.annotations.blobById(id)
            row = [ source.id, None, source.area, 0.0, source.class_name, "", "dead"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data.append(df)


        if len(sourceblobs) == 0:
            target = targetblobs[0]
            row = [None, target.id, 0.0, target.area, target.class_name, type, action]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data.append(df)

        elif len(targetblobs) == 0:
            source = sourceblobs[0]
            row = [source.id, None, source.area, 0, source.class_name, type, action]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data.append(df)

        else:
            #place new correspondences

            for source in sourceblobs:
                for target in targetblobs:
                    row = [source.id, target.id, source.area if source.id is not None else 0, target.area if target.id is not None else 0,
                           source.class_name if source.id is not None else target.class_name, type, action]
                    df = pd.DataFrame([row], columns=self.data.columns)
                    self.data.append(df)

#        print("final data", self.data)

    #startring for a blob will fin the cluster both in source and target
    def findCluster(self, blobid, is_source):
        # so we want source to be blob and target to be the other viewerplus.
        source = "Blob 1"
        target = "Blob 2"
        if not is_source:
            source, target = target, source

        #involved rows
        rows = []
        # find all blobs in the target connected to the blob
        data = self.data
        linked = data.loc[data[source] == blobid]
        targetcluster = []
        for index, row in linked.iterrows():
            targetid = row[target]
            if targetid is None:
                continue
            targetcluster.append(targetid)
            rows.append(index)

        # find all the connected in the source connected to the selected targets
        sourcecluster = [blobid]
        linked = data.loc[data[target].isin(targetcluster)]
        for index, row in linked.iterrows():
            sourceid = row[source]
            if sourceid is None:
                continue
            sourcecluster.append(sourceid)
            rows.append(index)

        if not is_source:
            sourcecluster, targetcluster = targetcluster, sourcecluster

        return (sourcecluster, targetcluster, rows)

    def autoMatch(self, blobs1, blobs2):

        for blob1 in blobs1:
            for blob2 in blobs2:
                # use bb to quickly calculate intersection
                x1 = max(blob1.bbox[0], blob2.bbox[0])
                y1 = max(blob1.bbox[1], blob2.bbox[1])
                x2 = min(blob1.bbox[0] + blob1.bbox[3], blob2.bbox[0] + blob2.bbox[3])
                y2 = min(blob1.bbox[1] + blob1.bbox[2], blob2.bbox[1] + blob2.bbox[2])
                # compute the area of intersection rectangle
                interArea = abs(max((x2 - x1, 0)) * max((y2 - y1), 0))

                if interArea != 0 and blob2.class_name == blob1.class_name and blob1.class_name != 'Empty':
                    # this is the get mask function for the outer contours, I put it here using two different if conditions so getMask just runs just on intersections
                    mask1 = Blob.getMask(blob1)
                    sizeblob1 = np.count_nonzero(mask1)
                    mask2 = Blob.getMask(blob2)
                    sizeblob2 = np.count_nonzero(mask2)
                    minblob = min(sizeblob1, sizeblob2)
                    intersectionArea = np.count_nonzero(intersectMask(mask1, blob1.bbox, mask2, blob2.bbox))

                    if (intersectionArea < (0.6 * minblob)):
                        continue
                    if (sizeblob2 > sizeblob1 * self.threshold):
                        self.correspondences.append([blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'grow', 'none'])

                    elif (sizeblob2 < sizeblob1 / self.threshold):
                        self.correspondences.append([blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'shrink', 'none'])

                    else:
                        self.correspondences.append([blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'same', 'none'])


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
            all_blobs.append(int(blobs1[i].id))

        for j in range(0, len(self.correspondences)):
            existing.append(int(self.correspondences[j][0]))

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
            all_blobs.append(int(blobs2[i].id))

        for j in range(0, len(self.correspondences)):
            existing.append(int(self.correspondences[j][1]))

        missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs2[index].class_name != 'Empty':
                self.born.append([None, id, 0.0, blobs2[index].area, blobs2[index].class_name, 'born', 'none'])