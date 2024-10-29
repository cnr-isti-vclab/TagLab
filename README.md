# TagLab: an image segmentation tool oriented to marine data analysis

| &nbsp; [Software Requirements](#software-requirements) &nbsp; | &nbsp; [Install](#installing-taglab) &nbsp; | &nbsp; [Update](#updating-taglab) &nbsp; | &nbsp; [Citation](#citation) &nbsp; |

TagLab was developed to assist with the annotation and extraction of statistical data from ortho-maps of benthic communities. The tool features various AI segmentation networks specifically trained for agnostic recognition (focused solely on contours) and semantic recognition (which also considers species) of corals. TagLab is an ongoing project of the [Visual Computing Lab](http://vcg.isti.cnr.it/)
![ScreenShot](screenshot.jpg)


## Interaction

TagLab allows users to interactively segment regions using the following methods:

- [`DEXTR: Four-Clicks Tool`](https://github.com/scaelles/DEXTR-PyTorch): This tool involves indicating the extremes of regions with four clicks. It utilizes the `Deep Extreme Cut` model, which has been fine-tuned for complex structures.
- [`RITM: Positive-Negative Clicks Tool`](https://github.com/saic-vul/ritm_interactive_segmentation): This tool enables users to define the interior and exterior of a region through positive and negative clicks. It utilizes the `Reviving Iterative Training with Mask Guidance` model, which has been train to work across various domains.
- [`SAM: Positive-Negative Clicks Tool`](https://github.com/facebookresearch/segment-anything): This tool allows for indicating the interior and exterior of a region within a sub-window using positive and negative clicks. It utilizes the `Segment Anything` model, which has been trained to work across various domains.
- [`SAM: All Regions in an Area Tool`](https://github.com/facebookresearch/segment-anything): This tool allows users to segment all regions inside a sub-window by automatically placing region seeds. It utilizes the `Segment Anything` model, which has been trained to work across various domains.

## Fully Automated Segmentation

TagLab enables users to automatically segment regions by using a custom segmentation model, which are trained using the 
[`DeepLab V3+`](https://github.com/jfzhang95/pytorch-deeplab-xception) backbone. Using a custom model in TagLab is 
accomplished through the following steps:

1. Creating and managing a training dataset
2. Training a model using the `Train Your Network` interface
3. Making predictions with the `Fully Automated Semantic Segmentation` tool

TagLab has many resources for image data management and analysis, including the ability to track changes among time 
points. For additional information, please visit the official TagLab website and documentation 
[page](https://taglab.isti.cnr.it/)

## Software Requirements

TagLab runs on __Linux__, __Windows__, and __MacOS__. To run TagLab, the main requirement is just __64bit Python 3.11.x__.

GPU accelerated computations are not supported on MacOS and on any machine that does not have an NVIDIA graphics card 
with CUDA enabled. To use them, you will need to install the __NVIDIA CUDA Toolkit__, versions 9.2, 10.1, 10.2, 11.0, 
11.1, 11.3 and 11.6 are supported. If you do not have a NVIDIA graphics card with CUDA enabled (or if you use MacOS), 
CPU will be used.

## Installing TagLab

See the instructions on the [wiki](https://github.com/cnr-isti-vclab/TagLab/wiki/Install-TagLab).

## Updating TagLab

If you already installed TagLab and you need to update to a new version, you can just run the `update.py` script from 
the terminal (be sure to be into the TagLab main folder, see step 2):

```bash
python3 update.py
```
or, on Windows:

```bash
python.exe update.py
```

The script will automatically update TagLab to the newest version available in this repository.

NOTE: If some package is missing, after an update, re-launch `install.py`.

### Updating from 0.2

If you are updating TagLab from 0.2 version, in order to download also the new networks, please run the `update.py` 
script twice:

```bash
python3 update.py
python3 update.py
```


# Citation

If you use TagLab, please cite it.

```
@article{TagLab,
	author = {Pavoni, Gaia and Corsini, Massimiliano and Ponchio, Federico and Muntoni, Alessandro and Edwards, Clinton and Pedersen, Nicole and Sandin, Stuart and Cignoni, Paolo},
	title = {TagLab: AI-assisted annotation for the fast and accurate semantic segmentation of coral reef orthoimages},
	year = {2022},
	journal = {Journal of Field Robotics},
	volume = {39},
	number = {3},
	pages = {246 – 262},
	doi = {10.1002/rob.22049}
}
```