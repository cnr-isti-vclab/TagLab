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
        self.data = pd.DataFrame(data = correspondences, columns=['Genet', 'Blob1', 'Blob2', 'Area1', 'Area2', 'Class', 'Action', 'Split\Fuse'])

    def area_in_sq_cm(self, area, is_source):

        if is_source:
            area_sq_cm = area * self.source.pixelSize() * self.source.pixelSize() / 100.0
        else:
            area_sq_cm = area * self.target.pixelSize() * self.target.pixelSize() / 100.0

        return area_sq_cm

    def isGenetInfoAvailable(self):

        if len(self.data.index) < 2:
            return False

        if self.data.loc[1, 'Genet'] >= 0:
            return True
        else:
            return False

# this is done in genet.py, since we need to update ALL the coorespondences.
 #   def updateGenets(self):
 #       for index, row in self.data.iterrows():
 #           id1 = int(row['Blob1'])
 #           id2 = int(row['Blob2'])
 #           blob1 = self.source.annotations.blobById(id1)
 #           blob2 = self.target.annotations.blobById(id2)

#            if blob1 is not None:
#                if blob1.genet is not None:
#                    self.data.loc[index, 'Genet'] = blob1.genet
#            else:
#                if blob2.genet is not None:
#                    self.data.loc[index, 'Genet'] = blob2.genet

    def updateAreas(self, use_surface_area=False):

        for index, row in self.data.iterrows():
            id1 = int(row['Blob1'])
            id2 = int(row['Blob2'])
            action = row['Action']
            blob1 = self.source.annotations.blobById(id1)
            blob2 = self.target.annotations.blobById(id2)

            if blob1 is None and blob2 is None:
                print("BOOM")

            # WHAT ??
            #self.data.loc[index, 'Class'] = blob1.class_name if blob1 is not None else blob2.class_name

            area1 = 0
            if blob1 is not None:
                area_pixel = blob1.area
                if use_surface_area:
                    area_pixel = blob1.surface_area
                area1 = self.area_in_sq_cm(area_pixel, True)
            self.data.loc[index, 'Area1'] = area1

            area2 = 0
            if blob2 is not None:
                area_pixel = blob2.area
                if use_surface_area:
                    area_pixel = blob2.surface_area
                area2 = self.area_in_sq_cm(area_pixel, False)
            self.data.loc[index, 'Area2'] = area2

            # update grow/shrink information
            if action == "grow" or action == "shrink" or action == "same":
                if area2 > area1*self.threshold:
                    self.data.loc[index, 'Action'] = "grow"
                elif area2 < area1 / self.threshold:
                    self.data.loc[index, 'Action'] = "shrink"
                else:
                    self.data.loc[index, 'Action'] = "same"

    def setSurfaceAreaValues(self):

        for index, row in self.data.iterrows():
            id1 = int(row['Blob1'])
            id2 = int(row['Blob2'])
            blob1 = self.source.annotations.blobById(id1)
            blob2 = self.target.annotations.blobById(id2)
            if blob1 is not None:
                self.data.loc[index, 'Area1'] = self.area_in_sq_cm(blob1.area, True)
            if blob2 is not None:
                self.data.loc[index, 'Area2'] = self.area_in_sq_cm(blob2.area, False)

    def save(self):
        return { "source": self.source.id, "target": self.target.id, "correspondences": self.data.values.tolist() }

    def sort_data(self):

        self.data.sort_values(by=['Action', 'Blob1', 'Blob2'], inplace=True, ignore_index=True)

    def checkTable(self):
        """
        Table may contain inconsistencies. This function check and remove them.
        """

        inconsistencies = False
        current_table = self.data.copy()
        for index, row in current_table.iterrows():
            id1 = int(row['Blob1'])
            id2 = int(row['Blob2'])
            blob1 = self.source.annotations.blobById(id1)
            blob2 = self.target.annotations.blobById(id2)

            if blob1 is None and blob2 is None:
                self.data.drop(index, inplace=True)
                inconsistencies = True

        return inconsistencies

    def fillTable(self, lst):
        """
        Fill the table from a list of correspondences.
        """

        if not lst:
            return

        if len(lst[0]) == 7:
            # genet information is missing..
            for ll in lst:
                ll.insert(0, -1)

        columns = self.data.columns
        self.data = pd.DataFrame(lst, columns=columns)

        self.checkTable()

        #this is needed to ensure consistency between blob data and correspondences data (WHICH SHOULD NOT BE REPLICATED!!!!)
        #FIXME! this is also pretty expensive when loading data!
        self.updateAreas()

        self.sort_data()

    def addBlob(self, image, blob):

        if self.source == image:
            self.set([blob], [])
        else:
            self.set([], [blob])

    def removeBlob(self, image, blob):
        if self.source == image:
            self.set([blob], [])
            self.data = self.data[self.data['Blob1'] != blob.id]
        else:
            self.set([], [blob])
            self.data = self.data[self.data['Blob2'] != blob.id]

        self.data.reset_index(drop=True, inplace=True)

    def updateBlob(self, image, old_blob, new_blob):
        if old_blob.class_name != new_blob.class_name:
            if self.source == image:
                set(self, [new_blob], [])
            else:
                set(self, [], [new_blob])
            return
        if self.source == image:
            self.data.loc[self.data["Blob1"] == old_blob.id, "Blob1"] = new_blob.id
            self.data.loc[self.data["Blob1"] == old_blob.id, "Area1"] = self.area_in_sq_cm(new_blob.area, False)
        else:
            self.data.loc[self.data["Blob2"] == old_blob.id, "Blob2"] = new_blob.id
            self.data.loc[self.data["Blob2"] == old_blob.id, "Area2"] = self.area_in_sq_cm(new_blob.area, False)
 
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
            #we need to check if the orphaned has other relationships.
            relatives = self.data[self.data['Blob2'] == id]
            if len(relatives):
                continue
            target = self.target.annotations.blobById(id)
            row = [-1, -1, target.id, 0.0, self.area_in_sq_cm(target.area, False), target.class_name, "born", type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

        for id in sourceorphaned:
            if id < 0:
                continue
            #we need to check if the orphaned has other relationships.
            relatives = self.data[self.data['Blob1'] == id]
            if len(relatives):
                continue
            source = self.source.annotations.blobById(id)
            row = [-1, source.id, -1, self.area_in_sq_cm(source.area, True), 0.0, source.class_name, "dead", type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

        if len(sourceblobs) == 0:
            target = targetblobs[0]
            row = [-1, -1, target.id, 0.0, self.area_in_sq_cm(target.area, False), target.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

        elif len(targetblobs) == 0:
            source = sourceblobs[0]
            row = [-1, source.id, -1, self.area_in_sq_cm(source.area, True), 0.0, source.class_name, action, type]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

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
                    row = [-1, source.id, target.id, source_area, target_area, class_name, action, type]
                    df = pd.DataFrame([row], columns=self.data.columns)
                    self.data = pd.concat([self.data, df])

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
            row = [-1, blob.id, -1, self.area_in_sq_cm(blob.area, True), 0.0, blob.class_name, "dead", "none"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

        for i in set(born):
            blob = self.target.annotations.blobById(i)
            row = [-1, -1, blob.id, 0.0, self.area_in_sq_cm(blob.area, False), blob.class_name, "dead", "none"]
            df = pd.DataFrame([row], columns=self.data.columns)
            self.data = pd.concat([self.data, df])

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
                    mask, bbox = intersectMask(mask1, blob1.bbox, mask2, blob2.bbox)
                    intersectionArea = np.count_nonzero(mask)

                    if (intersectionArea < (0.6 * minblob)):
                        continue
                    if (sizeblob2 > sizeblob1 * self.threshold):
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'grow', 'none'])

                    elif (sizeblob2 < sizeblob1 / self.threshold):
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'shrink', 'none'])

                    else:
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, blob1.class_name, 'same', 'none'])


        # operates on the correspondences found and update them
        self.assignSplit()
        self.assignFuse()

        # fill self.born and self.dead blob lists
        self.assignDead(blobs1)
        self.assignBorn(blobs2)


    def autoMatchM(self, blobs1, blobs2):
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

                if interArea != 0 and blob1.class_name != 'Empty':
                    # this is the get mask function for the outer contours, I put it here using two different if conditions so getMask just runs just on intersections
                    mask1 = Blob.getMask(blob1)
                    sizeblob1 = np.count_nonzero(mask1)
                    mask2 = Blob.getMask(blob2)
                    sizeblob2 = np.count_nonzero(mask2)
                    minblob = min(sizeblob1, sizeblob2)
                    mask, bbox = intersectMask(mask1, blob1.bbox, mask2, blob2.bbox)
                    intersectionArea = np.count_nonzero(mask)

                    class_name = blob1.class_name + "-" + blob2.class_name

                    if (intersectionArea < (0.2 * minblob)):
                        continue

                    if (sizeblob2 > sizeblob1 * self.threshold):
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, class_name, 'grow', 'none'])

                    elif (sizeblob2 < sizeblob1 / self.threshold):
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, class_name, 'shrink', 'none'])

                    else:
                        self.correspondences.append([-1, blob1.id, blob2.id, blob1.area, blob2.area, class_name, 'same', 'none'])


        # operates on the correspondences found and update them
        self.assignSplit()
        self.assignFuse()

        # fill self.born and self.dead blob lists
        self.assignDead(blobs1)
        self.assignBorn(blobs2)

        ##### ANALYZE CASES ######

        # Classes are "Pocillopora" and "Pocillopora_dead"

        # 1) D → D
        # 2) D → ∅      (NO MATCH)
        # 3) D or ∅ → L (newborns)
        # 4) L → D       (dead and disappeared)
        # 5) L → ∅      (NO MATCH)
        # 6) L → PD      (PD=partially dead. I will mark this colony as partially dead and then consider only the amount of new dead surface).
        # 7) PD → PD
        # 8) PD → D
        # 9) ∅ → D (error, or suddenly dead)

        # NOTE: case 7 and case 8 now are not considered (!)

        # ADJUST NAMES
        for corresp in self.correspondences:

            class_name = corresp[5]
            class_name1 = corresp[5].split("-")[0]
            class_name2 = corresp[5].split("-")[1]

            if class_name1 == "Pocillopora_dead" and class_name2 == "Pocillopora":
                class_name = "TO CHECK"   # RESURRECTION (!)  (D -> L)

            if class_name1 == "Pocillopora_dead" and class_name2 == "Pocillopora_dead":
                class_name = "DISCARDED"  # case 1 [D → D (discarded)]

            corresp[5] = class_name

        for born in self.born:
            class_name = born[5]
            if class_name == "Pocillopora":
                born[5] = "newborn"    # case 3 [D or ∅ → L (newborns)]
            if class_name == "Pocillopora_dead":
                born[5] = "TO CHECK"   # case 9 [∅ → D (error, or suddenly dead)]

        for dead in self.dead:
            class_name = dead[5]
            if class_name == "Pocillopora":
                dead[5] = "NO MATCH"   # case 5   [L → ∅ (NO MATCH)]
            if class_name == "Pocillopora_dead":
                dead[5] = "DISCARDED"  # case 2   [D → ∅ (DISCARDED)]

        ##### CREATE TABLE AND SAVE IT

        lines = self.correspondences + self.dead + self.born
        self.data = pd.DataFrame(lines, columns=self.data.columns)
        self.sort_data()
        self.data.to_csv("partially_dead.csv", index=False)


        # CHECK IF LIVE POCILLOPORA REMAINS LIVE, BECAME PARTIALLY DEAD, OR TOTALLY DEAD

        id_set = set()
        for corresp in self.correspondences:
            class_name = corresp[5]
            if class_name.find("-") > 0:
                class_name1 = corresp[5].split("-")[0]
                class_name2 = corresp[5].split("-")[1]
                if class_name1 == "Pocillopora":
                    id = corresp[1]
                    id_set.add(id)

        ids = list(id_set)  # list of ids to check

        area_pocillopora_live = 0.0
        area_pocillopora_dead = 0.0
        area_partially_dead_live = 0.0
        area_partially_dead_dead = 0.0
        area_proportion = 0.0
        live = 0
        partially_dead = 0
        totally_dead = 0
        live_data = []
        partially_dead_data = []
        dead_data = []
        for id in ids:
            matches = self.data[self.data['Blob1'] == id]

            area_live = 0.0
            area_dead = 0.0
            for index, row in matches.iterrows():
                class_name = row['Class']
                class_name1 = class_name.split("-")[0]
                class_name2 = class_name.split("-")[1]
                if class_name2 == "Pocillopora":
                    area_live += row['Area2']
                else:
                    area_dead += row['Area2']

            if area_live > 0.0 and area_dead > 0.0:
                # case 6 [L -> PD]
                partially_dead += 1
                area_partially_dead_live += area_live
                area_partially_dead_dead += area_dead
                area_proportion += ((100.0*area_dead) / (area_dead + area_live))

                for index, row in matches.iterrows():
                    partially_dead_data.append([row['Blob1'], row['Blob2'], row['Area1'], row['Area2'], row['Split\Fuse']])

            if area_dead < 0.00001:
                # case L -> L
                live += 1
                area_pocillopora_live += area_live

                for index, row in matches.iterrows():
                    live_data.append([row['Blob1'], row['Blob2'], row['Area1'], row['Area2'], row['Split\Fuse']])

            if area_live < 0.00001:
                # case L -> D
                totally_dead += 1
                area_pocillopora_dead += area_dead

                for index, row in matches.iterrows():
                    dead_data.append([row['Blob1'], row['Blob2'], row['Area1'], row['Area2'], row['Split\Fuse']])


        area_proportion = area_proportion / partially_dead

        data1 = pd.DataFrame(data = live_data, columns=['Blob1', 'Blob2', 'Area1', 'Area2', 'Split\Fuse'])
        data2 = pd.DataFrame(data = partially_dead_data, columns=['Blob1', 'Blob2', 'Area1', 'Area2', 'Split\Fuse'])
        data3 = pd.DataFrame(data = dead_data, columns=['Blob1', 'Blob2', 'Area1', 'Area2', 'Split\Fuse'])

        data1.to_csv("2018-2019-plot16-live.csv", index=False)
        data2.to_csv("2018-2019-plot16-partially_dead.csv", index=False)
        data3.to_csv("2018-2019-plot16-dead.csv", index=False)

        ##### COMPUTE STATISTICS

        disappear = 0
        born = 0
        area_disappear = 0.0
        area_born = 0.0
        discarded = 0
        area_discarded = 0.0
        tocheck = 0
        area_tocheck = 0.0
        total_area1 = 0.0
        total_area2 = 0.0
        for index,row in self.data.iterrows():

            if row['Class'] == "newborn":
                born += 1
                area_born += row['Area2']

            if row['Class'] == "NO MATCH":
                disappear += 1
                area_disappear += row['Area1']

            if row['Class'] == "DISCARDED":
                discarded += 1

                if row['Area2'] < 0.00001:
                    area_discarded += row['Area2']
                else:
                    area_discarded += row['Area2']

            if row['Class'] == "TO CHECK":
                tocheck += 1
                if row['Area2'] < 0.00001:
                    area_tocheck += row['Area2']
                else:
                    area_tocheck += row['Area2']

            if row["Blob2"] < 0:
                total_area1 += row['Area1']
            else:
                total_area1 += row['Area2']

        total_area2 = area_pocillopora_live + area_partially_dead_live + area_partially_dead_dead + area_pocillopora_dead + area_born + area_disappear + area_discarded + area_tocheck

        print("Pocillopora live             (L -> L)        : {:d} ({:.2f} cm^2)".format(live, area_pocillopora_live))
        print("Pocillopora partially dead   (L -> PD)       : {:d} (live {:.2f} cm^2) ; dead {:.2f} cm^2) ; % dead {:.2f}".format(partially_dead, area_partially_dead_live,
                                                                               area_partially_dead_dead, area_proportion))
        print("Pocillopora totally dead     (L -> D)        : {:d} ({:.2f} cm^2)".format(totally_dead, area_pocillopora_dead))
        print("Pocillopora born             (∅ -> L)        : {:d} ({:.2f} cm^2)".format(born, area_born))
        print("")

        print("NO MATCH (live or dead)      (D,L → ∅)       : {:d} ({:.2f} cm^2)".format(disappear, area_disappear))
        print("DISCARDED                    (D -> D, ∅)     : {:d} ({:.2f} cm^2)".format(discarded, area_discarded))
        print("TO CHECK                     (∅ → D, D -> L) : {:d} ({:.2f} cm^2)".format(tocheck, area_tocheck))
        print("")

        print("Total area                                    : {:.2f} cm^2".format(total_area2))


    def assignSplit(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][1]))
        splitted = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][1]) in splitted:
                self.correspondences[i][7] = 'split'


    def assignFuse(self):

        mylist = []
        for i in range(0, len(self.correspondences)):
            mylist.append(int(self.correspondences[i][2]))
        fused = sorted(set([i for i in mylist if mylist.count(i) > 1]))

        for i in range(0, len(self.correspondences)):
            if int(self.correspondences[i][2]) in fused:
                self.correspondences[i][7] = 'fuse'


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
            existing.append(int(self.correspondences[j][1]))

        missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs1[index].class_name != 'Empty':
                self.dead.append([-1, id, -1,  blobs1[index].area, 0.0, blobs1[index].class_name, 'dead', 'none'])


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
            existing.append(int(self.correspondences[j][2]))

        missing = [i for i in all_blobs if i not in existing]

        for id in missing:
            index = all_blobs.index(id)
            if blobs2[index].class_name != 'Empty':
                self.born.append([-1, -1, id, 0.0, blobs2[index].area, blobs2[index].class_name, 'born', 'none'])

