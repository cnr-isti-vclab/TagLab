
import numpy as np

from PyQt5.QtGui import QImage


def qimage2ndarray(image):
    w = image.width()
    h = image.height()
    fmt = image.format()

    arr = np.zeros((h, w, 3), dtype=np.uint8)

    if fmt == QImage.Format_RGB32:
        bits = image.bits()
        bits.setsize(h*w*4)
        arrtemp = np.frombuffer(bits, np.uint8).copy()
        arrtemp = np.reshape(arrtemp, [h, w, 4])
        arr[:, :, 0] = arrtemp[:, :, 2]
        arr[:, :, 1] = arrtemp[:, :, 1]
        arr[:, :, 2] = arrtemp[:, :, 0]

    elif fmt == QImage.Format_ARGB32:
        pass

    return arr


def ndarray2qimage(image):
    h = image.shape[0]
    w = image.shape[1]
    ch = image.shape[2]

    imgdata = np.zeros([h, w, 4], dtype=np.uint8)

    if ch == 3:
        imgdata[:, :, 2] = image[:, :, 0]
        imgdata[:, :, 1] = image[:, :, 1]
        imgdata[:, :, 0] = image[:, :, 2]
        imgdata[:, :, 3] = 255
        qimg = QImage(imgdata.data, w, h, QImage.Format_RGB32)

    elif ch == 4:
        imgdata[:, :, 3] = image[:, :, 0]
        imgdata[:, :, 2] = image[:, :, 1]
        imgdata[:, :, 1] = image[:, :, 2]
        imgdata[:, :, 0] = image[:, :, 3]
        qimg = QImage(imgdata.data, w, h, QImage.Format_ARGB32)

    return qimg.copy()