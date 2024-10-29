# TagLab: an image segmentation tool oriented to marine data analysis

| &nbsp; [Software Requirements](#software-requirements) &nbsp; | &nbsp; [Install](#installing-taglab) &nbsp; | &nbsp; [Update](#updating-taglab) &nbsp; | &nbsp; [Citation](#citation) &nbsp; |

TagLab was developed to assist with the annotation and extraction of statistical data from ortho-maps of benthic communities. The tool features various AI segmentation networks specifically trained for agnostic recognition (focused solely on contours) and semantic recognition (which also considers species) of corals. TagLab is an ongoing project of the Visual Computing Lab http://vcg.isti.cnr.it/
![ScreenShot](screenshot.jpg)


## Interaction

TagLab allows users to interactively segment regions using the following methods:

- Four-Clicks Tool: This method involves indicating the extremes of regions with four clicks. It utilizes the Deep Extreme Cut network, which has been fine-tuned for complex structures. You can find the original code for Deep Extreme Cut here: https://github.com/scaelles/DEXTR-PyTorch.
- Positive-Negative Clicks Tool: This tool enables users to define the interior and exterior of a region through positive and negative clicks. It is based on the RITM interactive segmentation project. Additional information and the code can be found here: https://github.com/saic-vul/ritm_interactive_segmentation.
- SAM Positive/Negative Clicks: This method allows for indicating the interior and exterior of a region within a sub-window using positive and negative clicks. More details can be found on the SAM webpage: https://segment-anything.com/.
- SAM All Regions in an Area: Users can segment all regions inside a sub-window only by placing region seeds. This technique also utilizes the SAM approach. For more information, please visit the SAM webpage: https://segment-anything.com/.a coral using the positive-negative clicks tool. Use shift+left mouse button to assign the positive (the interior) points and shift+right mouse button to assign the negative (the exterior) points. This tool is based on the RITM interactive segmentation project, code and additional information can be found here: https://github.com/saic-vul/ritm_interactive_segmentation


TagLab enables users to automatically segment regions by utilizing custom recognition models. This is accomplished through the following steps:

- Creating and managing a training dataset
- Training the model using the 'Train Your Network' interface
- Inferring predictions with the 'Fully Automated Semantic Segmentation' tool

This learning pipeline is used as a backbone of the DeepLab V3+ , https://github.com/jfzhang95/pytorch-deeplab-xception/.


TagLab has many resources for image data management and analysis and the ability to track changes among time points. For additional information, please visit the website and the documentation: https://taglab.isti.cnr.it/


## Software Requirements


TagLab runs on __Linux__, __Windows__, and __MacOS__. To run TagLab, the main requirement is just __64bit Python 3.7.x, 3.8.x or 3.9.x__.

GPU accelerated computations are not supported on MacOS and on any machine that has not an NVIDIA graphics card.
To use them, you'll need to install the __NVIDIA CUDA Toolkit__, versions 9.2, 10.1, 10.2, 11.0, 11.1, 11.3 and 11.6 are supported.
If you don't have a NVida graphics card (or if you use MacOS), CPU will be used.

## Installing TagLab

See the instructions on the [wiki](https://github.com/cnr-isti-vclab/TagLab/wiki/Install-TagLab).

## Updating TagLab

If you already installed TagLab and you need to update to a new version, you can just run the `update.py` script from the terminal (be sure to be into the TagLab main folder, see step 2):

```
python3 update.py
```
or, on Windows:

```
python.exe update.py
```

The script will automatically update TagLab to the newest version available in this repository.

NOTE: If some package is missing, after an update, re-launch install.py .

### Updating from 0.2

If you are updating TagLab from 0.2 version, in order to download also the new networks, please run the `update.py` script twice:

```
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
