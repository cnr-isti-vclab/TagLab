import matplotlib.pyplot as plt
from scipy import stats
import numpy as np
import random
import PIL.ImageDraw as ImageDraw
import PIL.Image as Image
import os.path
#from tqdm import tqdm
import math
import seaborn as sns
import pandas as pd

def plotRGBHistogram(image, title):

    img_R = image[:,:,0]
    data_R = pd.DataFrame(data=img_R.reshape(-1), columns=['Value'])
    data_R['Color'] = 'Red'
    img_G = image[:,:,1]
    data_G = pd.DataFrame(data=img_G.reshape(-1), columns=['Value'])
    data_G['Color'] = 'Green'
    img_B = image[:, :, 2]
    data_B = pd.DataFrame(data=img_B.reshape(-1), columns=['Value'])
    data_B['Color'] = 'Blue'

    data_R = data_R.append(data_G)
    data_R = data_R.append(data_B)
    data_R = data_R.reset_index()

    #ax = sns.histplot(data=data_R, x="Value", hue="Color", multiple="stack", kde=True)
    ax = sns.kdeplot(data=data_R, x="Value", hue="Color", multiple="stack")
    ax.set_title(title)
    filename = "kde-L=90-" + title + ".png"
    ax.get_figure().savefig(filename)

def load_images():
    img_path = 'C:\\temp\\test\\'
    imgs = []
    for file in os.listdir(img_path):
        imgs.append(np.array(Image.open(img_path + file)))
    # both input images are from 0-->255
    return imgs

def print_histogram(_histrogram, name, title):
    plt.figure()
    plt.title(title)
    plt.plot(_histrogram, color='#ef476f')
    plt.bar(np.arange(len(_histrogram)), _histrogram, color='#b7b7a4')
    plt.ylabel('Number of Pixels')
    plt.xlabel('Pixel Value')
    plt.savefig("hist_" + name)


def generate_histogram(img, print, index):
    # if len(img.shape) == 3: # img is colorful
    #     gr_img = np.mean(img, axis=-1)
    # else:
    gr_img = img
    '''now we calc grayscale histogram'''
    gr_hist = np.zeros([256])
    tot_pix = 0
    for x_pixel in range(gr_img.shape[0]):
        for y_pixel in range(gr_img.shape[1]):
            pixel_value = int(gr_img[x_pixel, y_pixel])
            # ESCLUDO LO SFONDO - CONTO SOLO PIXEL non neri e non bianchi
            if pixel_value > 0 and pixel_value < 255:
               tot_pix = tot_pix + 1
               gr_hist[pixel_value] += 1
    '''normalize Histogram'''
    # gr_hist /= (gr_img.shape[0] * gr_img.shape[1])
    gr_hist /= tot_pix

    # if print:
    #     print_histogram(gr_hist, name="neq_"+str(index), title="Normalized Histogram")
    return gr_hist, gr_img


def equalize_histogram(img, histo, L):
    eq_histo = np.zeros_like(histo)
    # en_img = np.zeros_like(img)
    for i in range(len(histo)):
        eq_histo[i] = int(round((L - 1) * np.sum(histo[0:i])))
    # print_histogram(eq_histo, name="eq_"+str(index), title="Equalized Histogram")
    '''enhance image as well:'''
    # for x_pixel in range(img.shape[0]):
    #     for y_pixel in range(img.shape[1]):
    #         pixel_val = int(img[x_pixel, y_pixel])
    #         en_img[x_pixel, y_pixel] = eq_histo[pixel_val]

    '''creating new histogram'''
    # hist_img, _ = generate_histogram(en_img, print=False, index=index)
    # print_img(img=en_img, histo_new=hist_img, histo_old=histo, index=str(index), L=L)
    return eq_histo


def find_value_target(val, target_arr):
    print(val)
    key = np.where(target_arr == val)[0]
    if len(key) == 0:
        if val < max(target_arr):
           key = find_value_target(val+1, target_arr)
        else:
            key = find_value_target(val-1, target_arr)
    vvv = key[0]
    print(vvv)

    return vvv


def match_histogram(inp_img, hist_input, e_hist_input, e_hist_target, _print=True):
    '''map from e_inp_hist to 'target_hist '''
    en_img = np.zeros_like(inp_img)
    tran_hist = np.zeros_like(e_hist_input)
    for i in range(len(e_hist_input)):
        tran_hist[i] = find_value_target(val=e_hist_input[i], target_arr=e_hist_target)
    # print_histogram(tran_hist, name="trans_hist_", title="Transferred Histogram")
    '''enhance image as well:'''
    for x_pixel in range(inp_img.shape[0]):
        for y_pixel in range(inp_img.shape[1]):
            pixel_val = int(inp_img[x_pixel, y_pixel])
            en_img[x_pixel, y_pixel] = tran_hist[pixel_val]
    '''creating new histogram'''
    # hist_img, _ = generate_histogram(en_img, print=False, index=3)
    # print_img(img=en_img, histo_new=hist_img, histo_old=hist_input, index=str(3), L=L)
    return en_img


if __name__ == '__main__':
    L=90
    print("\r\nLoading Images:")
    imgs = load_images()
    print("\r\ngenerating HistogramS:")
    matched = np.zeros_like(imgs[0])
    for i in range(0,3):
        gr_img_arr = []
        gr_hist_arr = []
        eq_hist_arr = []
        index = 0
        for img in imgs:
            img = img[:,:,i]
            #returns gray image and gray scale histogram
            hist_img, gr_img = generate_histogram(img, print=True, index=index)
            gr_hist_arr.append(hist_img)
            gr_img_arr.append(gr_img)
            eq_hist_arr.append(equalize_histogram(gr_img, hist_img, L))
            index += 1
        en_img = match_histogram(inp_img=gr_img_arr[0], hist_input=gr_hist_arr[0], e_hist_input=eq_hist_arr[0], e_hist_target=eq_hist_arr[1])
        matched[:, :, i] = en_img

    plt.imsave('image_new.jpg',matched )

    fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(8, 3),
                                        sharex=True, sharey=True)
    for aa in (ax1, ax2, ax3):
        aa.set_axis_off()

    ax1.imshow(imgs[0])
    ax1.set_title('Source')
    ax2.imshow(imgs[1])
    ax2.set_title('Reference')
    ax3.imshow(matched)
    ax3.set_title('Matched')

    plt.tight_layout()
    plt.show()

    plt.figure()
    plotRGBHistogram(imgs[0], 'Input')
    plt.figure()
    plotRGBHistogram(imgs[1], 'Target')
    plt.figure()
    plotRGBHistogram(matched, 'Matched')

    print('fatto')