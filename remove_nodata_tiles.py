import os
import sys
import glob
import time
import argparse
from PIL import Image
import numpy as np
import shutil

def discard_image_tiles_with_uniform_background(input_folder, output_folder):

    path = os.path.join(input_folder, "images")
    images_names = [x for x in glob.glob(os.path.join(path, '*.png'))]

    for image_name in images_names:

        print("Processing tile ", image_name)

        pil_img = Image.open(image_name)
        img = np.array(pil_img)

        red = img[:,:,0]
        green = img[:,:,1]
        blue = img[:,:,2]

        total_variance = np.var(red) + np.var(green) + np.var(blue)
        if total_variance < 10.0:
            # the background is uniform
            basename = os.path.basename(image_name)
            outimg = os.path.join(output_folder, basename)
            shutil.move(image_name, outimg)


if __name__ == '__main__':

    """
    All the RGB tiles that do not contain information (uniform background) will be removed from the training dataset.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_folder", type=str, default="", help="Folder containing the dataset")
    args = parser.parse_args()

    ##### SETUP

    DATASET_FOLDER = args.dataset_folder

    print("THE TILES DISCARDED WILL BE MOVED TO THE FOLLOWING FOLDERS: \n"
          "training -> discarded/training_discarded\n"
          "validation -> validation_discarded\n"
          "test -> test_discarded\n")

    TRAINING_FOLDER = os.path.join(DATASET_FOLDER, "training")
    VALIDATION_FOLDER = os.path.join(DATASET_FOLDER, "validation")
    TEST_FOLDER = os.path.join(DATASET_FOLDER, "test")

    OUTPUT_FOLDER = os.path.join(DATASET_FOLDER, "discarded")
    TRAINING_OUTPUT_FOLDER = os.path.join(OUTPUT_FOLDER, "training")
    VALIDATION_OUTPUT_FOLDER = os.path.join(OUTPUT_FOLDER, "validation")
    TEST_OUTPUT_FOLDER = os.path.join(OUTPUT_FOLDER, "test")

    if not os.path.exists(TRAINING_FOLDER):
        print("Training folder does not exists (!)")
        sys.exit(-1)

    if not os.path.exists(VALIDATION_FOLDER):
        print("Validation folder does not exists (!)")
        sys.exit(-1)

    if not os.path.exists(TEST_FOLDER):
        print("Test folder does not exists (!)")
        sys.exit(-1)

    # create output folders
    if not os.path.exists(OUTPUT_FOLDER):
        os.mkdir(OUTPUT_FOLDER)

    if not os.path.exists(TRAINING_OUTPUT_FOLDER):
        os.mkdir(TRAINING_OUTPUT_FOLDER)

    if not os.path.exists(VALIDATION_OUTPUT_FOLDER):
        os.mkdir(VALIDATION_OUTPUT_FOLDER)

    if not os.path.exists(TEST_OUTPUT_FOLDER):
        os.mkdir(TEST_OUTPUT_FOLDER)


    ##### DISCARD TILES

    start = time.time()

    discard_image_tiles_with_uniform_background(TRAINING_FOLDER, TRAINING_OUTPUT_FOLDER)
    discard_image_tiles_with_uniform_background(VALIDATION_FOLDER, VALIDATION_OUTPUT_FOLDER)
    discard_image_tiles_with_uniform_background(TEST_FOLDER, TEST_OUTPUT_FOLDER)

    end = time.time()

    txt = "Total processing time {:.2f} seconds".format(end-start)
    print(txt)



