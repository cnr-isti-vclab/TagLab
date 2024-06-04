# This script filters the tiles of a training dataset according to different criterias.


import numpy as np
import PIL.Image as Image
import os
import glob
import random
import shutil


DATASET_IMAGES = "C:\\Users\\Max\\Documents\\KKopecky\\DATASET_2024\\training\\images"
DATASET_LABELS = "C:\\Users\\Max\\Documents\\KKopecky\\DATASET_2024\\training\\labels"
DATASET_FILTERED_IMAGES = "C:\\Users\\Max\\Documents\\KKopecky\\DATASET_2024\\training_filtered\\images"
DATASET_FILTERED_LABELS = "C:\\Users\\Max\\Documents\\KKopecky\\DATASET_2024\\training_filtered\\labels"

def remove_if_not_contains(images_list, target_class_color, perc):
    """
    Remove a percentage of the tiles if not contains a specific class.
    If perc=100 all the tiles that not contain a specific class are removed.
    """

    for image_path in images_list:

        print(image_path)

        pil_img = Image.open(image_path)
        img = np.array(pil_img)

        npixels = img.shape[0] * img.shape[1]

        res = np.where((img[:,:,0] == target_class_color[0]) & (img[:,:,1] == target_class_color[1]) & (img[:,:,2] == target_class_color[2]))
        pixels = np.count_nonzero(res)

        p = pixels / npixels
        coin = random.randint(0, 99)

        # at the minimum 0.1% should of the target class should be present
        if p > 0.001:
            image_filename = os.path.basename(image_path)

            img_src = os.path.join(DATASET_IMAGES, image_filename)
            img_dest = os.path.join(DATASET_FILTERED_IMAGES, image_filename)

            label_src = os.path.join(DATASET_LABELS, image_filename)
            label_dest = os.path.join(DATASET_FILTERED_LABELS, image_filename)

            shutil.copy(img_src, img_dest)
            shutil.copy(label_src, label_dest)
        elif coin > perc:
            image_filename = os.path.basename(image_path)

            img_src = os.path.join(DATASET_IMAGES, image_filename)
            img_dest = os.path.join(DATASET_FILTERED_IMAGES, image_filename)

            label_src = os.path.join(DATASET_LABELS, image_filename)
            label_dest = os.path.join(DATASET_FILTERED_LABELS, image_filename)

            shutil.copy(img_src, img_dest)
            shutil.copy(label_src, label_dest)

if __name__ == '__main__':

    images_names = glob.glob(os.path.join(DATASET_LABELS, '*.png'))

    try:
        os.makedirs(DATASET_FILTERED_IMAGES)
    except:
        pass

    try:
        os.makedirs(DATASET_FILTERED_LABELS)
    except:
        pass

    ##### SHUFFLE
    N_tiles = len(images_names)
    for k in range(10000):
        i = random.randint(0, N_tiles-1)
        j = random.randint(0, N_tiles-1)
        temp_name = images_names[j]
        images_names[j] = images_names[i]
        images_names[i] = temp_name

    ##### FILTERING

    remove_if_not_contains(images_names, target_class_color=[133, 96, 168], perc=70)





