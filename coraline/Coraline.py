import ctypes as C
from ctypes import cdll

try:
	lib = cdll.LoadLibrary('coraline/libcoraline.so')
except:
	lib = None

import numpy as np

class Coraline(object):
	def __init__(self, img, mask):
		if lib is None:
			raise Exception("Coraline library (libcoraline.so) not found.")
		w = img.shape[1]
		h = img.shape[0]
		W = mask.shape[1]
		H = mask.shape[0]
		if (w != W) or (h != H):
			print(w, h, W, H)
			exit(0)

		self.obj = lib.Coraline_new(C.c_void_p(img.ctypes.data), C.c_void_p(mask.ctypes.data), C.c_int(w), C.c_int(h))

	def __del__(self):
		lib.Coraline_delete(self.obj)

	def setImg(self, img):
		w = C.c_int(img.shape[1])
		h = C.c_int(img.shape[0])
		lib.Coraline_setImg(self.obj, C.c_void_p(img.ctypes.data), w, h)

	def setMask(self, mask):
		w = C.c_int(mask.shape[1])
		h = C.c_int(mask.shape[0])
		lib.Coraline_setMask(self.obj, C.c_void_p(mask.ctypes.data), w, h)

	def setPred(self, pred):
		w = C.c_int(pred.shape[1])
		h = C.c_int(pred.shape[0])
		lib.Coraline_setPred(self.obj, C.c_void_p(pred.ctypes.data), w, h)

	def setLambda(self, l):
		lib.Coraline_setLambda(self.obj, C.c_float(l))

	def setConservative(self, conservative):
		lib.Coraline_setConservative(self.obj, C.c_float(conservative))

	def segment(self):
		w = 100
		h = 100
		data = lib.Coraline_segment(self.obj)
		data = C.cast(data, C.POINTER(C.c_ubyte))
		mask = np.ctypeslib.as_array(data, shape=(w, h))
		return mask




#mask = np.zeros((100,100))
#image =  np.zeros((100, 100))
#coraline = Coraline(image, mask)
#mask = coraline.segment()
#print(mask)
