import os
import sys
import glob
import json
import time
from PyQt5.QtCore import QDir, QSize
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


def applyClassifier(input_image, classifier_to_use, taglab_project, prediction_th, autocolor_flag, autolevels_flag, output_label_maps):

    # setup the desired classifier

    progress_printer = ProgressPrinter(input_image.name)

    classifier = MapClassifier(classifier_to_use, taglab_project.labels)
    classifier.updateProgress.connect(progress_printer.updateProgress)

    # rescaling the map to fit the target scale of the network

    RGB_channel = input_image.getRGBChannel()
    RGB_channel.loadData()
    w = RGB_channel.qimage.width()
    h = RGB_channel.qimage.height()
    target_pixel_size = classifier_to_use['Scale']
    classifier.setup(RGB_channel.qimage, input_image.pixelSize(), target_pixel_size,
                     working_area=taglab_project.working_area, padding=256)

    # runs the classifier
    classifier.run(1026, 513, 256, prediction_threshold=prediction_th,
                   save_scores=False, autocolor=autocolor_flag, autolevel=autolevels_flag)

    if classifier.flagStopProcessing is False:

        filename = os.path.join("temp", "labelmap.png")

        offset = classifier.offset
        scale = [classifier.scale_factor, classifier.scale_factor]
        created_blobs = input_image.annotations.import_label_map(filename, taglab_project.labels, offset, scale)

        for blob in created_blobs:
            input_image.annotations.seg_blobs.append(blob)

        if output_label_maps == 1:
            filename = input_image.name + ".png"
            fileout = os.path.join(OUTPUT_FOLDER, filename)
            input_image.annotations.export_image_data_for_Scripps(QSize(w, h), fileout, taglab_project)
        elif output_label_maps == 2:
            filename = input_image.name + ".png"
            fileout = os.path.join(OUTPUT_FOLDER, filename)
            wa = taglab_project
            taglab_project.working_area = [0, 0, w, h]  # update working area to the entire map
            input_image.annotations.export_image_data_for_Scripps(QSize(w, h), fileout, taglab_project)
            taglab_project.working_area = wa  # restore working area

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
    parser.add_argument("--output-label-maps", type=int, default=1, help="0: Not saved | 1: working area is saved | 2: entire map is saved")
    parser.add_argument("--autocolor", type=bool, default=False, help="Automatic color adjustment")
    parser.add_argument("--autolevels", type=bool, default=False, help="Automatic level adjustments")

    args = parser.parse_args()

    ##### CONFIGURATION

    PROJECTS_FOLDER = args.projects_folder
    OUTPUT_FOLDER = args.output_folder
    OUTPUT_LABEL_MAPS = args.output_label_maps
    CLASSIFIER_NAME = args.classifier_name
    AUTOCOLOR = args.autocolor
    AUTOLEVELS = args.autolevels
    PREDICTION_THRESHOLD = 0.5

    print("")
    print("* CONFIGURATION *")
    print("")

    print("Projects folder:", PROJECTS_FOLDER)
    print("Output folder:", OUTPUT_FOLDER)

    if OUTPUT_LABEL_MAPS == 0:
        print("Output label maps: Label maps are not saved.")
    elif OUTPUT_LABEL_MAPS == 1:
        print("Output label maps: For each map, the label map corresponding to the working area is saved.")
    else:
        print("Output label maps: For each map, the entire label maps is saved.")

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

    if not os.path.exists(PROJECTS_FOLDER):
        print("Projects folder does not exists (!)")
        sys.exit(-1)

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
            applyClassifier(image, selected_classifier, project, PREDICTION_THRESHOLD,
                            AUTOCOLOR, AUTOLEVELS, OUTPUT_LABEL_MAPS)
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



