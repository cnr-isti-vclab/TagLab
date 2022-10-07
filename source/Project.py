import os
import pandas as pd
import datetime
import json
import numpy as np

from PyQt5.QtCore import QDir, QFileInfo
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from source.Image import Image
from source.Channel import Channel
from source.Annotation import Annotation
from source.Shape import Layer, Shape
from source.Blob import Blob
from source.Label import Label
from source.Correspondences import Correspondences
from source.Genet import Genet
from source import utils
from source.Grid import Grid
from source.RegionAttributes import RegionAttributes

def loadProject(taglab_working_dir, filename, default_dict):

    dir = QDir(taglab_working_dir)
    filename = dir.relativeFilePath(filename)
    f = open(filename, "r")
    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        raise Exception(str(e))


    if "Map File" in data:
        project = loadOldProject(taglab_working_dir, data)
        project.loadDictionary(default_dict)
        project.region_attributes = RegionAttributes()
    else:
        project = Project(**data)

    f.close()

    if project.dictionary_name == "":
        project.dictionary_name = "My dictionary"

    project.filename = filename

    # check if a file exist for each image and each channel

    for image in project.images:
        for channel in image.channels:
            if not os.path.exists(channel.filename):
                (filename, filter) = QFileDialog.getOpenFileName(None, "Couldn't find "+ channel.filename + " please select it:", taglab_working_dir,
                                                                 "Image Files (*.png *.jpg *.jpeg *.tif *.tiff)")
                dir = QDir(taglab_working_dir)
                if image.georef_filename == channel.filename:
                   image.georef_filename = dir.relativeFilePath(filename)

                channel.filename = dir.relativeFilePath(filename)

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

    # ensure all maps have a name
    count = 1
    for im in project.images:
        if im.name is None or im.name == "":
            im.name = "noname{:02d}".format(count)
        count += 1

    # pixel size MUST BE a string
    im.map_px_to_mm_factor = str(im.map_px_to_mm_factor)

    # ensure all maps have an acquisition date
    for im in project.images:
        if not utils.isValidDate(im.acquisition_date):
            im.acquisition_date = "1955-11-05"

    # ensure the maps are ordered by the acquisition date
    project.orderImagesByAcquisitionDate()

    return project

# WARNING!! The old-style projects do not include a labels dictionary
def loadOldProject(taglab_working_dir, data):

    project = Project()
    map_filename = data["Map File"]

    #convert to relative paths in case:
    dir = QDir(taglab_working_dir)
    map_filename = dir.relativeFilePath(map_filename)
    image_name = os.path.basename(map_filename)
    image_name = image_name[:-4]
    image = Image(id=image_name)
    image.map_px_to_mm_factor = data["Map Scale"]
    image.acquisition_date = "1955-11-05"
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
        elif isinstance(obj, Layer):
            return obj.save()
        elif isinstance(obj, Shape):
            return obj.save()
        elif isinstance(obj, Correspondences):
            return obj.save()
        elif isinstance(obj, Grid):
            return obj.save()
        elif isinstance(obj, Genet):
            return {}
        elif isinstance(obj, RegionAttributes):
            return obj.save()
        return json.JSONEncoder.default(self, obj)

class Project(object):

    def __init__(self, filename=None, labels={}, images=[], correspondences=None,
                 spatial_reference_system=None, metadata={}, image_metadata_template={}, genet={},
                 dictionary_name="", dictionary_description="", working_area=None, region_attributes={}):

        self.filename = None                                             #filename with path of the project json

        # area of the images where the user annotate the data
        # NOTE 1: since the images are co-registered the working area is the same for all the images
        # NOTE 2: the working area is a RECTANGULAR region stored as [top, left, width, height]
        self.working_area = working_area

        self.dictionary_name = dictionary_name
        self.dictionary_description = dictionary_description

        self.labels = { key: Label(**value) for key, value in labels.items() }
        if not 'Empty' in self.labels:
            self.labels['Empty'] = Label(id='Empty', name='Empty', description=None, fill=[127, 127, 127], border=[200, 200, 200], visible=True)

        # compatibility with previous TagLab versions (working_area does not exist anymore)
        for img in images:
            if img.get("working_area") is not None:
                img.__delitem__("working_area")

        self.images = list(map(lambda img: Image(**img), images))       #list of annotated images

                                                                         # dict of tables (DataFrame) of correspondences betweeen a source and a target image

        self.correspondences = {}
        if correspondences is not None:
            for key in correspondences.keys():
                source = correspondences[key]['source']
                target = correspondences[key]['target']
                self.correspondences[key] = Correspondences(self.getImageFromId(source), self.getImageFromId(target))
                self.correspondences[key].fillTable(correspondences[key]['correspondences'])

        self.genet = Genet(self)
        self.region_attributes = RegionAttributes(**region_attributes)
        
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


    # def checkDictionaryConsistency(self, labels):
    #     """
    #     Check the consistency between a list of labels and the current annotations.
    #     """
    #
    #     messages = ""
    #     inconsistencies = 0
    #
    #     # check for existing labels present in the annotations but not present in list of labels
    #
    #     for class_name in class_names:
    #         if not class_name in labels:
    #             msg = "\n" + str(inconsistencies) + ") Label '" + key + "' is missing. We automatically add it."
    #             messages += msg
    #             inconsistencies += 1
    #
    #             label = self.labels[class_name]
    #             labels.append(label.copy())
    #
    #     if inconsistencies > 0:
    #         box = QMessageBox()
    #         box.setWindowTitle("There are dictionary inconsistencies. See below:\n")
    #         box.setText(messages)
    #         box.exec()
    #
    #     return True


    def labelsInUse(self):
        """
        It returns the labels currently assigned to the annotations.
        """

        class_names = set()  # class names effectively used
        for image in self.images:
            for blob in image.annotations.seg_blobs:
                class_names.add(blob.class_name)

        if len(class_names) == 0:
            return []
        else:
            return list(class_names)


    def save(self, filename = None):

        # check inconsistencies. They can be caused by bugs during the regions update/editing
        if self.correspondences is not None:
            for key in self.correspondences.keys():
                if self.correspondences[key].checkTable() is True:
                    # there are inconsistencies, THIS MUST BE NOTIFIED
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle("INCONSISTENT CORRESPONDENCES")
                    msgBox.setText("Inconsistent correspondences has been found !!\nPlease, Notify this problem to the TagLab developers.")
                    msgBox.exec()

        data = self.__dict__
        str = json.dumps(data, cls=ProjectEncoder, indent=1)

        if filename is None:
            filename = self.filename
        f = open(filename, "w")
        f.write(str)
        f.close()
        #except Exception as a:
        #    print(str(a))

    def loadDictionary(self, filename):

        f = open(filename)
        dictionary = json.load(f)
        f.close()

        self.dictionary_name = dictionary['Name']
        self.dictionary_description = dictionary['Description']
        labels = dictionary['Labels']

        self.labels = {}
        for label in labels:
            id = label['id']
            name = label['name']
            fill = label['fill']
            border = label['border']
            description = label['description']
            self.labels[name] = Label(id=id, name=name, fill=fill, border=border)

    def setDictionaryFromListOfLabels(self, labels):
        """
        Convert the list of labels into a labels dictionary.
        """

        self.labels = {}

        label_names = []
        for label in labels:
            label_names.append(label.name)

        # 'Empty' key must be be always present
        if not 'Empty' in label_names:
            self.labels['Empty'] = Label(id='Empty', name='Empty', description=None, fill=[127, 127, 127],
                                         border=[200, 200, 200], visible=True)

        for label in labels:
            self.labels[label.name] = label

    def classColor(self, class_name):
        if class_name == "Empty":
            return [127, 127, 127]
        if not class_name in self.labels:
            raise ("Missing label for " + class_name)
        return self.labels[class_name].fill

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
            print("WARNING! Unknown label: " + id)

        lbl = self.labels.get(id)
        return self.labels[id].visible

    def orderImagesByAcquisitionDate(self):
        """
        Order the image list by the acquisition date, from the oldest to the newest.
        """
        if self.images is not None:
            if len(self.images) > 1:
                image_list = self.images
#                image_list.sort(key=lambda x: datetime.date.fromisoformat(x.acquisition_date))
                image_list.sort(key=lambda x: datetime.datetime.strptime(x.acquisition_date, '%Y-%m-%d'))

                self.images = image_list

    def addNewImage(self, image):
        """
        Annotated images in the image list are sorted by date.
        """
        self.images.append(image)
        self.orderImagesByAcquisitionDate()

    def deleteImage(self, image):
        self.images = [i for i in self.images if i != image]
        self.correspondences = {key: corr for key, corr in self.correspondences.items() if corr.source != image and corr.target != image}

    def findCorrespondences(self, image):

        corresps = list(filter(lambda i, image=image: i.source == image or i.target == image,
                               self.correspondences.values()))
        return corresps

    def updateGenets(self, img_source_idx, img_target_idx):
        """
        Update the genets information in (1) the regions and (2) in the correspondences' table
        """
        self.genet.updateGenets()
        corr = self.getImagePairCorrespondences(img_source_idx, img_target_idx)
        #this is done in genet.py
        #corr.updateGenets()
        return corr

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
        else:
            corr = self.correspondences.get(key)
            if corr is None:
                # create a new correspondences table
                self.correspondences[key] = Correspondences(self.images[img_source_idx], self.images[img_target_idx])

        return self.correspondences[key]


    def addCorrespondence(self, img_source_idx, img_target_idx, blobs1, blobs2):
        """
        Add a correspondences to the current ones.
        """

        corr = self.getImagePairCorrespondences(img_source_idx, img_target_idx)
        corr.set(blobs1, blobs2)
        self.genet.updateGenets()
        #corr.updateGenets() moved to genet


    def updatePixelSizeInCorrespondences(self, image, flag_surface_area):

        correspondences= self.findCorrespondences(image)
        for corr in correspondences:
            corr.updateAreas(use_surface_area=flag_surface_area)
    
    def computeCorrespondences(self, img_source_idx, img_target_idx):
        """
        Compute the correspondences between an image pair.
        """

        conversion1 = self.images[img_source_idx].pixelSize()
        conversion2 = self.images[img_target_idx].pixelSize()

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

        self.genet.updateGenets()
        #corr.updateGenets() moved to genet


    def create_labels_table(self, image):

        '''
        It creates a data table for the label panel.
        If an active image is given, some statistics are added.
        '''

        dict = {
            'Visibility': np.zeros(len(self.labels), dtype=np.int),
            'Color': [],
            'Class': [],
            '#': np.zeros(len(self.labels), dtype=np.int),
            'Coverage': np.zeros(len(self.labels),dtype=np.float)
        }

        for i, key in enumerate(list(self.labels.keys())):
            label = self.labels[key]
            dict['Visibility'][i] = int(label.visible)
            dict['Color'].append(str(label.fill))
            dict['Class'].append(label.name)

            if image is None:
                count = 0
                new_area = 0.0
            else:
                count, new_area = image.annotations.calculate_perclass_blobs_value(label, image.pixelSize())

            dict['#'][i] = count
            dict['Coverage'][i] = new_area

        # create dataframe
        df = pd.DataFrame(dict, columns=['Visibility', 'Color', 'Class', '#', 'Coverage'])
        return df





