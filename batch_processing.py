import os
import sys
import glob
import json
import time
from PyQt5.QtCore import QDir
from source.Project import Project, loadProject
import torch
import argparse
from source.Image import Image
from source.MapClassifier import MapClassifier

class ProgressPrinter(object):

    def __init__(self, image_name):
        self.image_name = image_name

    def updateProgress(self, progress):

        txt = "Classification of image '{:s}' ({:.2f}%)".format(self.image_name, progress)
        print(txt)


def applyClassifier(input_image, classifier_to_use, labels, prediction_th, autocolor_flag, autolevels_flag):

    # setup the desired classifier

    progress_printer = ProgressPrinter(input_image.name)

    classifier = MapClassifier(classifier_to_use, labels)
    classifier.updateProgress.connect(progress_printer.updateProgress)

    # rescaling the map to fit the target scale of the network

    RGB_channel = input_image.getRGBChannel()
    RGB_channel.loadData()
    target_pixel_size = classifier_to_use['Scale']
    classifier.setup(RGB_channel.qimage, input_image.pixelSize(), target_pixel_size,
                     working_area=project.working_area, padding=256)

    # runs the classifier
    classifier.run(1026, 513, 256, prediction_threshold=prediction_th,
                   save_scores=False, autocolor=autocolor_flag, autolevel=autolevels_flag)

    if classifier.flagStopProcessing is False:

        filename = os.path.join("temp", "labelmap.png")

        offset = classifier.offset
        scale = [classifier.scale_factor, classifier.scale_factor]
        created_blobs = input_image.annotations.import_label_map(filename, labels, offset, scale)

        for blob in created_blobs:
            input_image.annotations.seg_blobs.append(blob)

    # reset GPU memory
    torch.cuda.empty_cache()
    if classifier is not None:
        del classifier
        classifier = None

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("--projects_folder", type=str, default="", help="Folder containing the input projects")
    parser.add_argument("--classifier_name", type=str, default="", help="Classifier to use")
    parser.add_argument("--output_folder", type=str, default="", help="Output of the classification")
    parser.add_argument("--autocolor", type=bool, default=False, help="Automatic color adjustment")
    parser.add_argument("--autolevels", type=bool, default=False, help="Automatic level adjustments")

    args = parser.parse_args()

    ##### CONFIGURATION

    PROJECTS_FOLDER = args.projects_folder
    OUTPUT_FOLDER = args.output_folder
    CLASSIFIER_NAME = args.classifier_name
    AUTOCOLOR = args.autocolor
    AUTOLEVELS = args.autolevels
    PREDICTION_THRESHOLD = 0.5

    if not os.path.exists(PROJECTS_FOLDER):
        print("Projects folder does not exists (!)")
        sys.exit(-1)

    print("")
    print("* CONFIGURATION *")
    print("")

    print("Projects folder:", PROJECTS_FOLDER)
    print("Output folder:", OUTPUT_FOLDER)
    print("Classifier: ", CLASSIFIER_NAME)
    if AUTOCOLOR:
        print("Automatic color balance: YES")
    else:
        print("Automatic color balance: NO")

    if AUTOLEVELS:
        print("White balance: YES")
    else:
        print("White balance: NO")

    print("------------------------------------------------")
    print("")

    taglab_dir = os.getcwd()
    default_dictionary = "dictionaries/scripps.json"

    # load existing classifiers
    f = open("config.json", "r")
    config_dict = json.load(f)
    available_classifiers = config_dict["Available Classifiers"]
    selected_classifier = None
    for classifier in available_classifiers:
        if classifier["Classifier Name"] == CLASSIFIER_NAME:
            selected_classifier = classifier

    if selected_classifier is None:
        print("You must select a valid classifier.")
        exit(-2)

    # create output folder if it does not exists
    if not os.path.exists(OUTPUT_FOLDER):
        os.mkdir(OUTPUT_FOLDER)

    # create projects list
    projects = [x for x in glob.glob(os.path.join(PROJECTS_FOLDER, '*.json'))]

    ##### MAIN LOOP - run automatic recognition on all the images of all the projects and save the result

    start = time.time()

    for project_filename in projects:

        # load project
        print("Loading project ->", os.path.basename(project_filename))
        project = loadProject(taglab_dir, project_filename, default_dictionary)

        # apply the classifier
        for image in project.images:

            pstart = time.time()
            applyClassifier(image, selected_classifier, project.labels, PREDICTION_THRESHOLD, AUTOCOLOR, AUTOLEVELS)
            pend = time.time()

            txt = "Image classified in {:.2f} seconds".format(pend-pstart)
            print(txt)

        # save project
        print("Save result")
        filename = os.path.basename(project.filename)
        fileout = os.path.join(OUTPUT_FOLDER, filename)
        dir = QDir(taglab_dir)
        project.filename = dir.relativeFilePath(fileout)
        project.save()

    end = time.time()

    txt = "Total procesing time {.2f} seconds".format(end-start)
    print(txt)



