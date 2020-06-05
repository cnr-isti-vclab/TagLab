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
    #ensure all maps have an ID:
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
    print(image_name)
    image.map_px_to_mm_factor = data["Map Scale"]
    image.metadata['acquisition_date'] = data["Acquisition Date"]
    channel = Channel(filename=map_filename, type="rgb")
    image.channels.append(channel)

    for blob_data in data["Segmentation Data"]:
        blob = Blob(None, 0, 0, 0)
        blob.fromDict(blob_data)
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

        return json.JSONEncoder.default(self, obj)



class Project(object):

    def __init__(self, filename = None, labels = {}, images = [], correspondences = None,
                 spatial_reference_system = None, metadata = {}, image_metadata_template = {}):
        self.filename = None        #filename with path of the project json
        self.labels = { key: Label(**value) for key, value in labels.items() }

        self.images = list(map(lambda img: Image(**img), images))       #list of annotated images
        self.correspondences = None
        corr = None if correspondences is None else correspondences['correspondences']
        print(correspondences)
        if len(self.images) > 1:
            self.correspondences = Correspondences(self.images[0], self.images[1], corr)   #list of correspondences betweeen labels in images
                                    #[ [source_img: , target_img:, [[23, 12, [grow, shrink, split, join] ... ] }
        self.spatial_reference_system = spatial_reference_system   #if None we assume coordinates in pixels (but Y is up or down?!)
        self.metadata = metadata    # project metadata => keyword -> value
        self.image_metadata_template = image_metadata_template  # description of metadata keywords expected in images
                                           # name: { type: (integer, date, string), mandatory: (true|false), default: ... }


    def importLabelsFromConfiguration(self, dictionary):
        """
        This function should be removed when the Labels Panel will be finished.
        """
        self.labels = {}
        for key in dictionary.keys():
            color = dictionary[key]
            self.labels[key] = Label(id=key, name=key, description=None, fill=color, border=[200, 200, 200], visible=True)


    def save(self, filename = None):
        #try:
        data = self.__dict__
        for img in self.images:
            print(img)
        str = json.dumps(data, cls=ProjectEncoder)

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


        print(self.labels[blob.class_name])
        color = self.labels[blob.class_name].fill
        brush = QBrush(QColor(color[0], color[1], color[2], 200))
        return brush


    def isLabelVisible(self, id):

        if id == "Empty":
            return True

        if not id in self.labels:
            raise Exception("Unknown label: " + id)

        return self.labels[id].visible



    def computeCorrespondences(self, idx1, idx2):

        conversion1 = self.images[idx1].map_px_to_mm_factor
        conversion2 = self.images[idx2].map_px_to_mm_factor

        # switch form px to mm just for calculation (except areas that are in cm)

        blobs1 = []
        for blob in self.images[idx1].annotations.seg_blobs:
            blob_c = blob.copy()
            blob_c.bbox = (blob_c.bbox*conversion1).round().astype(int)
            blob_c.contour = blob_c.contour*conversion1
            blob_c.area = blob_c.area*conversion1*conversion1/100
            blobs1.append(blob_c)

        blobs2 = []
        for blob in self.images[idx2].annotations.seg_blobs:
            blob_c = blob.copy()
            blob_c.bbox = (blob_c.bbox * conversion2).round().astype(int)
            blob_c.contour = blob_c.contour * conversion2
            blob_c.area = blob_c.area * conversion2 * conversion2 / 100
            blobs2.append(blob_c)

        corr = Correspondences(self.images[idx1], self.images[idx2])
        corr.autoMatch(blobs1, blobs2)
        corr.findSplit()
        corr.findFuse()

        corr.findDead(blobs1)
        corr.findBorn(blobs2)

        lines = corr.correspondences + corr.dead + corr.born
        for row in lines:
            corr.data = pd.concat([pd.DataFrame([row], columns=corr.data.columns), corr.data])

        self.correspondences = corr

        output_file = "correspondences_" + self.images[idx1].id + "-" + self.images[idx2].id + ".csv"
        corr.data.to_csv(output_file, index=False)

