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
        self.data = pd.DataFrame(data = correspondences, columns=['Blob1', 'Blob2', 'Area1', 'Area2', 'Class', 'Action', 'Split\Fuse'])


    def area_in_sq_cm(self, area, is_source):

        if is_source:
            area_sq_cm = area * self.source.map_px_to_mm_factor * self.source.map_px_to_mm_factor / 100.0
        else:
            area_sq_cm = area * self.target.map_px_to_mm_factor * self.target.map_px_to_mm_factor / 100.0

        return area_sq_cm

    def save(self):
        return { "source": self.source.id, "target": self.target.id, "correspondences": self.data.values.tolist() }

    def sort_data(self):

        self.data.sort_values(by=['Action', 'Blob1', 'Blob2'], inplace=True, ignore_index=True)

    def fillTable(self, lst):
        """
        Fill the table from a list of correspondences.
        """

        columns = self.data.columns
        self.data = pd.DataFrame(lst, columns=columns)
        self.sort_data()


    def set(self, sourceblobs, targetblobs):

        #assumes one oth the two list has 1 blob only.
        type = "n/s"
        action = "n/s"
        if len(sourceblobs) == 0:
            action = "born"
            type = "none"
        elif len(targetblobs) == 0:
            action = "dead"
            type = "none"
        elif len(sourceblobs) > 1:
            type = "fuse"
        elif len(targetblobs) > 1:
            type = "split"
        elif sourceblobs[0].area > targetblobs[0].area*self.threshold:
            action = "shrink"
        elif sourceblobs[0].area < targetblobs[0].area/self.threshold:
            action = "grow"
        else:
            action = "same"
            #TODO consider morph!

        #orphaned nodes: not in sourceblob, but had some connections in  targetblobs (dead now) and viceversa
        #they will become born or dead
        targetorphaned = self.data[self.data['Blob1'].isin([b.id for b in sourceblobs])]['Blob2']
        sourceorphaned = self.data[self.data['Blob2'].isin([b.id for b in targetblobs])]['Blob1']

        targetorphaned = list(set(targetorphaned) - set([b.id for b in targetblobs]))
        sourceorphaned = list(set(sourceorphaned) - set([b.id for b in sourceblobs]))

        #remove all correspondences where orphaned
        self.data = self.data[self.data['Blob1'].isin([b.id for b in sourceblobs]) == False]
        self.data = self.data[self.data['Blob2'].isin([b.id for b in targetblobs]) == False]

        for id in targetorphaned:
            if id < 0: # born and dead result in orphaned
                continue
            target = self.target.annotations.blobById(id)
            row = [-1, target.id, 0.0, self.area_in_sq_cm(target.area, False), target.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        for id in sourceorphaned:
            if id < 0:
                continue
            source = self.source.annotations.blobById(id)
            row = [ source.id, -1, self.area_in_sq_cm(source.area, True), 0.0, source.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        if len(sourceblobs) == 0:
            target = targetblobs[0]
            row = [-1, target.id, 0.0, self.area_in_sq_cm(target.area, False), target.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        elif len(targetblobs) == 0:
            source = sourceblobs[0]
            row = [source.id, -1, self.area_in_sq_cm(source.area, True), 0, source.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        else:

            # place new correspondences
            for source in sourceblobs:
                for target in targetblobs:
                    source_area = 0.0
                    if source.id >= 0:
                        source_area = self.area_in_sq_cm(source.area, True)
                    target_area = 0.0
                    if target.id >= 0:
                        target_area = self.area_in_sq_cm(target.area, False)

                    class_name = source.class_name if source.id >= 0 else target.class_name
                    row = [source.id, target.id, source_area, target_area, class_name, action, type]
                    df = pd.DataFrame([row], columns=self.data.columns)
                    self.data = self.data.append(df)

        self.sort_data()


    # starting for a blob id will find the cluster both in source and target
    def findCluster(self, blobid, is_source):
        # so we want source to be blob and target to be the other viewerplus
        source = "Blob1"
        target = "Blob2"
        if not is_source:
            source, target = target, source

        sourcecluster = [blobid] # source ids
        targetcluster = []       # target ids
        rows = []                # involved rows

        # find all blobs in the target connected to the blob
        linked = self.data[self.data[source] == blobid]
        for index, row in linked.iterrows():
            targetid = row[target]
            if targetid >= 0:
                targetcluster.append(targetid)
            rows.append(index)

        # find all the connected in the source connected to the selected targets
        linked = self.data.loc[self.data[target].isin(targetcluster)]
        for index, row in linked.iterrows():
            sourceid = row[source]
            if sourceid >= 0:
                sourcecluster.append(sourceid)
            rows.append(index)

        if not is_source:
            sourcecluster, targetcluster = targetcluster, sourcecluster

        sourcecluster = list(set(sourcecluster))
        targetcluster = list(set(targetcluster))
        rows = list(set(rows))

        return sourcecluster, targetcluster, rows


    def deleteCluster(self, indexes):

        born = []
        dead = []
        for i in indexes:
            row = self.data.iloc[i]
            if row["Blob1"] >= 0:
                dead.append(row["Blob1"])
            if row["Blob2"] >= 0:
                born.append(row["Blob2"])

        # delete rows from the dataframe
        self.data.drop(indexes, inplace=True)

        # reindexing
        self.data.reset_index(drop=True, inplace=True)

        count = len(self.data.index)

        for i in set(dead):
            blob = self.source.annotations.blobById(i)
            row = [blob.id, -1, self.area_in_sq_cm(blob.area, True), 0.0, blob.class_name, "dead", "none"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        for i in set(born):
            blob = self.target.annotations.blobById(i)
            row = [-1, blob.id, 0.0, self.area_in_sq_cm(blob.area, False), blob.class_name, "dead", "none"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = self.data.append(df)

        self.sort_data()


    def autoMatch(self, blobs1, blobs2):
        self.correspondences.clear()
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


        # operates on the correspondences found and update them
        self.assignSplit()
        self.assignFuse()

        # fill self.born and self.dead blob lists
        self.assignDead(blobs1)
        self.assignBorn(blobs2)


    def assignSplit(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][0]))
        splitted = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][0]) in splitted:
                self.correspondences[i][6] = 'split'


    def assignFuse(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][1]))
        fused = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in fused:
                self.correspondences[i][6] = 'fuse'


    def assignDead(self, blobs1):

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
                self.dead.append([id, -1,  blobs1[index].area, 0.0, blobs1[index].class_name, 'dead', 'none'])


    def assignBorn(self, blobs2):

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
                self.born.append([-1, id, 0.0, blobs2[index].area, blobs2[index].class_name, 'born', 'none'])

