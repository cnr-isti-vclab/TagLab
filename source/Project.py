import os
import json

from PyQt5.QtCore import QDir
from PyQt5.QtGui import QBrush, QColor

from source.Image import Image
from source.Channel import Channel
from source.Blob import Blob


def loadProject(filename):
    f = open(filename, "r")
    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        raise Exception(str(e))

    if "Map File" in data:
        project =  loadOldProject(data)
    else:
        project = Project(**data)

    project.filename = filename
    f.close()
    return project

def loadOldProject(data):
    project = Project(filename = data["Project Name"])
    map_filename = data["Map File"]

    #convert to relative paths in case:
    dir = QDir(os.getcwd())
    map_filename = dir.relativeFilePath(map_filename)

    image = Image()
    image.map_px_to_mm_factor = data["Map Scale"]
    channel = Channel(filename=map_filename, type="rgb")
    image.channels.append(channel)

    for blobs in data["Segmentation Data"]:
        blob = Blob(None, 0, 0, 0)
        blob.fromDict(blobs)
        image.annotations.addBlob(blob)

    project.images.append(image)
    return project


class Project(object):
    def __init__(self, filename = None, labels = [], images = [], correspondences = [],
                 spatial_reference_system = None, metadata = {}, image_metadata_template = {}):
        self.filename = None        #filename with path of the project json
        self.labels = labels        #list of labels used in this project
        self.images = list(map(lambda img: Image(**img), images))       #list of annotated images
        self.correspondences = correspondences   #list of correspondences betweeen labels in images
                                    #[ [source_img: , target_img:, [[23, 12, [grow, shrink, split, join] ... ] }
        self.spatial_reference_system = spatial_reference_system   #if None we assume coordinates in pixels (but Y is up or down?!)
        self.metadata = metadata    # project metadata => keyword -> value
        self.image_metadata_template = image_metadata_template  # description of metadata keywords expected in images
                                           # name: { type: (integer, date, string), mandatory: (true|false), default: ... }

    def save(self):
        data = self.__dict__
        data["images"] = list(map(lambda img: img.save(), self.images))

        f = open(self.filename, "w")
        f.write(json.dumps(data))
        f.close()

    def classBrushFromName(self, blob):
        brush = QBrush()

        if not blob.class_name == "Empty":
            color = self.labels[blob.class_name]
            brush = QBrush(QColor(color[0], color[1], color[2], 200))
        return brush