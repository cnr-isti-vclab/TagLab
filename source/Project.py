import os
import json

from PyQt5.QtCore import QDir
from PyQt5.QtGui import QBrush, QColor

from source.Image import Image
from source.Channel import Channel
from source.Annotation import Annotation
from source.Blob import Blob
from source.Label import Label
from source.Correspondences import Correspondences
from source.Genet import Genet

import pandas as pd


def loadProject(filename, labels_dict):

    dir = QDir(os.getcwd())
    filename = dir.relativeFilePath(filename)
    f = open(filename, "r")
    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        raise Exception(str(e))


    if "Map File" in data:
        project = loadOldProject(data, labels_dict)
    else:
        project = Project(**data)

    project.filename = filename

    # load geo-reference information
    for im in project.images:
        if im.georef_filename != "":
            im.loadGeoInfo(im.georef_filename)

    # ensure all maps have an ID:
    count = 1
    for im in project.images:
        if im.id is None:
            im.id = "Map " + str(count)
        count += 1

    f.close()
    return project


# NOTE: old project NEEDS a pre-defined label dictionary
def loadOldProject(data, labels_dict):

    project = Project()
    project.importLabelsFromConfiguration(labels_dict)
    map_filename = data["Map File"]

    #convert to relative paths in case:
    dir = QDir(os.getcwd())
    map_filename = dir.relativeFilePath(map_filename)
    image_name = os.path.basename(map_filename)
    image_name = image_name[:-4]
    image = Image(id=image_name)
    image.map_px_to_mm_factor = data["Map Scale"]
    image.metadata['acquisition_date'] = data["Acquisition Date"]
    channel = Channel(filename=map_filename, type="RGB")
    image.channels.append(channel)

    for blob_data in data["Segmentation Data"]:
        blob = Blob(None, 0, 0, 0)
        blob.fromDict(blob_data)
        blob.setId(int(blob.id))  # id should be set again to update related info
        image.annotations.addBlob(blob)

    project.images.append(image)
    return project

class ProjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Image):
            return obj.save()
        elif isinstance(obj, Channel):
            return obj.save()
        elif isinstance(obj, Label):
            return obj.save()
        elif isinstance(obj, Annotation):
            return obj.save()
        elif isinstance(obj, Blob):
            return obj.save()
        elif isinstance(obj, Correspondences):
            return obj.save()
        elif isinstance(obj, Genet):
            return obj.save()

        return json.JSONEncoder.default(self, obj)

class Project(object):

    def __init__(self, filename=None, labels={}, images=[], correspondences=None,
                 spatial_reference_system=None, metadata={}, image_metadata_template={}):

        self.filename = None                                             #filename with path of the project json
        self.labels = { key: Label(**value) for key, value in labels.items() }
        if not 'Empty' in self.labels:
            self.labels['Empty'] = Label(id='Empty', name='Empty', description=None, fill=[127, 127, 127], border=[200, 200, 200], visible=True)

        self.images = list(map(lambda img: Image(**img), images))       #list of annotated images

                                                                         # dict of tables (DataFrame) of correspondences betweeen a source and a target image
        self.correspondences = {}
        if correspondences is not None:
            for key in correspondences.keys():
                source = correspondences[key]['source']
                target = correspondences[key]['target']
                self.correspondences[key] = Correspondences(self.getImageFromId(source), self.getImageFromId(target))
                self.correspondences[key].fillTable(correspondences[key]['correspondences'])

        self.spatial_reference_system = spatial_reference_system        #if None we assume coordinates in pixels (but Y is up or down?!)
        self.metadata = metadata                                        # project metadata => keyword -> value
        self.image_metadata_template = image_metadata_template          # description of metadata keywords expected in images
                                                                         # name: { type: (integer, date, string), mandatory: (true|false), default: ... }



    def importLabelsFromConfiguration(self, dictionary):
        """
        This function should be removed when the Labels Panel will be finished.
        """
        self.labels = {}
        if not 'Empty' in dictionary:
            self.labels['Empty'] = Label(id='Empty', name='Empty', description=None, fill=[127, 127, 127], border=[200, 200, 200], visible=True)
        for key in dictionary.keys():
            color = dictionary[key]
            self.labels[key] = Label(id=key, name=key, description=None, fill=color, border=[200, 200, 200], visible=True)


    def save(self, filename = None):
        #try:
        data = self.__dict__
        str = json.dumps(data, cls=ProjectEncoder, indent=1)

        if filename is None:
            filename = self.filename
        f = open(filename, "w")
        f.write(str)
        f.close()
        #except Exception as a:
        #    print(str(a))


    def classBrushFromName(self, blob):
        brush = QBrush()
        if blob.class_name == "Empty":
            return brush

        if not blob.class_name in self.labels:
            print("Missing label for " + blob.class_name + ". Creating one.")
            self.labels[blob.class_name] = Label(blob.class_name, blob.class_name, fill = [255, 0, 0])

        color = self.labels[blob.class_name].fill
        brush = QBrush(QColor(color[0], color[1], color[2], 200))
        return brush


    def isLabelVisible(self, id):
        if not id in self.labels:
            raise Exception("Unknown label: " + id)

        return self.labels[id].visible

    def findCorrespondences(self, image):

        corresps = list(filter(lambda i, image=image: i.source == image or i.target == image,
                               self.correspondences.values()))
        return corresps

    def addBlob(self, image, blob):

        # update image annotations
        image.annotations.addBlob(blob)

        # update correspondences
        for corr in self.findCorrespondences(image):
            corr.addBlob(image, blob)

    def removeBlob(self, image, blob):

        # updata image annotations
        image.annotations.removeBlob(blob)

        # update correspondences
        for corr in self.findCorrespondences(image):
            corr.removeBlob(image, blob)

    def updateBlob(self, image, old_blob, new_blob):

        # update image annotations
        image.annotations.updateBlob(old_blob, new_blob)

        # update correspondences
        for corr in self.findCorrespondences(image):
            corr.updateBlob(image, old_blob, new_blob)

    def setBlobClass(self, image, blob, class_name):
        blob.class_name = class_name
        # THIS should be removed: the color comes from the labels!
        blob.class_color = self.labels[blob.class_name].fill


        for corr in self.findCorrespondences(image):
            corr.setBlobClass(image, blob, class_name)


    def getImageFromId(self, id):
        for img in self.images:
            if img.id == id:
                return img
        return None

    def getImagePairCorrespondences(self, img_source_idx, img_target_idx):
        """
        Given two image indices returns the current correspondences table or create a new one.
        Note that the correspondences between the image A and the image B are not the same of
        the image B and A.
        """
        key = self.images[img_source_idx].id + "-" + self.images[img_target_idx].id

        if self.correspondences is None:
            # create a new correspondences table
            self.correspondences = {}
            self.correspondences[key] = Correspondences(self.images[img_source_idx], self.images[img_target_idx])
        elif not key in self.correspondences:
            # create a new correspondences table
            self.correspondences[key] = Correspondences(self.images[img_source_idx], self.images[img_target_idx])

        return self.correspondences[key]


    def addCorrespondence(self, img_source_idx, img_target_idx, blobs1, blobs2):
        """
        Add a correspondences to the current ones.
        """

        corr = self.getImagePairCorrespondences(img_source_idx, img_target_idx)
        corr.set(blobs1, blobs2)


    def computeCorrespondences(self, img_source_idx, img_target_idx):
        """
        Compute the correspondences between an image pair.
        """

        conversion1 = self.images[img_source_idx].map_px_to_mm_factor
        conversion2 = self.images[img_target_idx].map_px_to_mm_factor

        # switch form px to mm just for calculation (except areas that are in cm)

        blobs1 = []
        for blob in self.images[img_source_idx].annotations.seg_blobs:
            blob_c = blob.copy()
            blob_c.bbox = (blob_c.bbox*conversion1).round().astype(int)
            blob_c.contour = blob_c.contour*conversion1
            blob_c.area = blob_c.area*conversion1*conversion1 / 100
            blobs1.append(blob_c)

        blobs2 = []
        for blob in self.images[img_target_idx].annotations.seg_blobs:
            blob_c = blob.copy()
            blob_c.bbox = (blob_c.bbox * conversion2).round().astype(int)
            blob_c.contour = blob_c.contour * conversion2
            blob_c.area = blob_c.area * conversion2 * conversion2 / 100
            blobs2.append(blob_c)

        corr = self.getImagePairCorrespondences(img_source_idx, img_target_idx)
        corr.autoMatch(blobs1, blobs2)

        lines = corr.correspondences + corr.dead + corr.born
        corr.data = pd.DataFrame(lines, columns=corr.data.columns)
        corr.sort_data()
        corr.correspondence = []
        corr.dead = []
        corr.born =[]


