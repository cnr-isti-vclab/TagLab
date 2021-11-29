import numpy as np
import PIL.Image as Image
import os.path
import pickle

if __name__ == '__main__':

    img_path = 'C:\\ten-orthos-scripps-augmented-10-epochs'

    L=50
    print("\r\nLoading Images:")
    image_list = os.listdir(img_path)
    print("\r\ngenerating HistogramS:")
    img_arr = []
    eq_hist_arr = np.zeros((3,256))
    counter = 0
    for i in range(0,3):
        hist = np.zeros([256])
        tot_pix = 0
        for filename in image_list[0:10]:
            print(counter)
            img = np.array(Image.open(os.path.join(img_path, filename)))
            img = img[:,:,i]
            counter = counter + 1
            for x_pixel in range(img.shape[0]):
                for y_pixel in range(img.shape[1]):
                    pixel_value = int(img[x_pixel, y_pixel])
                    if pixel_value > 0 and pixel_value < 255:
                        tot_pix = tot_pix + 1
                        hist[pixel_value] += 1

        '''normalize Histogram'''
        hist = hist/tot_pix
        ''''equalize histogram'''''
        eq_hist = np.zeros_like(hist)
        for j in range(len(hist)):
            eq_hist[j] = int(round((L - 1) * np.sum(hist[0:j])))
        eq_hist_arr[i,:] = eq_hist


    # save the histogram
    f = open("hist.dat", "wb")
    pickle.dump(eq_hist_arr, f)
    f.close()

    # re-read the histogram
    f = open("hist.dat", "rb")
    hist = pickle.load(f)
    print(hist)
    f.close()
