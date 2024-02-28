# This script re-assemble image tiles in a single orthoimage.
#
# The tiles must have the same prefix and a progressive numbering.


import numpy as np
import PIL.Image as Image
import os

if __name__ == '__main__':

    # list of images to process. WARNING: put the path without the final numbers
    list_of_images = [
        "C:\\Users\\Max\\Documents\\RHONDA\\IMAGES\\HAR462_20230504_17M_ORTHO",
        "C:\\Users\\Max\\Documents\\RHONDA\\IMAGES\\PAT051_20210704_7M_ORTHO"
        ]

    output_folder = "C:\\temp4"

    for image_name in list_of_images:

        filename = image_name + "_{:0>4d}.png".format(1)
        pil_img = Image.open(filename)
        w = pil_img.width
        h = pil_img.height
        imgout = np.zeros((h * 2, w * 6, 3), np.uint8)

        output_name = os.path.join(output_folder, os.path.basename(image_name) + ".png")

        for c in range(6):
            for r in range(2):
                i = r + c * 2 + 1

                filename = image_name + "_{:0>4d}.png".format(i)
                print(filename)

                offy = h*(1-r)
                offx = w*c

                pil_img = Image.open(filename)
                img = np.array(pil_img)
                imgout[offy:offy+h, offx:offx+w, 0] = img[0:h, 0:w, 0]
                imgout[offy:offy+h, offx:offx+w, 1] = img[0:h, 0:w, 1]
                imgout[offy:offy+h, offx:offx+w, 2] = img[0:h, 0:w, 2]

        pil_img_out = Image.fromarray(imgout)
        pil_img_out.save(output_name)






