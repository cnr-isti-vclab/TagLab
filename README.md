# TagLab: an image segmentation tool oriented to marine data analysis

TagLab was created to support the activity of annotation and extraction of statistical data from ortho-maps of benthic communities. The tool includes different types of CNN-based segmentation networks specially trained for agnostic (relative only to contours) or semantic (also related to species) recognition of corals. TagLab is an ongoing project of the Visual Computing Lab http://vcg.isti.cnr.it/.

![ScreenShot](screenshot.jpg)


## Interaction
TagLab allows to :

- zoom and navigate a large map using (zoom/mouse wheel, pan/'Move' tool selected + left button). With every other tool selected the pan is activated with ctrl + left button
- segment coral instances in a semi-automatic way by simply clicks at the corals' extremes. This is achieved using the Deep Extreme Cut network fine-tuned on coral images. Deep Extreme Cut original code : https://github.com/scaelles/DEXTR-PyTorch/
- assign a class with the 'Assign class' tool. Area and perimeter are now displayed in the segmentation info panel on the right
- simultaneously turn off the visibility of one or more classes, (ctrl + left button/disable all but the selected, shift + left button, inverse operation), change the class transparency using the above slider
- perform boolean operations between existing labels (right button to open the menu)
- refine the incorrect borders automatically with the Refine operation or manually with the 'Edit Border' tool
- tracking coral changes in different time intervals
- import depth information of the seafloor
- import GeoTiff
- draw coral internal cracks with the 'Create Crack' tool
- make freehand measurements or measure the distance between centroids (Ruler tool).
- save the annotations (as polygons) and import them into a new project
- export a CSV file table containing the data of each coral colony
- export a JPG file of a black background with totally opaque labels
- export shapefiles
- export a new dataset and train your network (!)

We are working hard to create a web site with detailed instructions about TagLab. Stay tuned(!)


## Supported Platforms and Requirements
TagLab runs on __Linux__, __Windows__, and __MacOS__. To run TagLab, the main requirement is just __Python 3.6.x or 3.7.x__.

GPU accelerated computations are not supported on MacOS and on any machine that has not an NVIDIA graphics card.
To use them, you'll need to install the __NVIDIA CUDA Toolkit__, versions 9.2, 10.1 or 10.2 are supported.
If you don't have a NVida graphics card (or if you use MacOS), CPU will be used.

## Installing TagLab

### Step 0: Dependencies
Before installing TagLab, be sure to have installed __Python 3.6.x or 3.7.x__, and __NVIDIA CUDA Toolkit__ if it is supported. You can check if they are properly installed by running the following commands in a shell (bash on Linux, poweshell on Windows):

```
python3 --version
nvcc --version
```
If python and cuda are properly installed, both commands will print their versions.

Under Linux, if you don't use the APT package manager (not ubuntu or debian derived distros), be sure to install the gdal library manually (the command `gdal-config --version` should output the gdal library version).
Under MacOS, if you don't use HomeBrew package manager, be sure to install the gdal library manually (the command `gdal-config --version` should output the gdal library version).

Under MacOS and Linux, also __*cmake*__ and a C++ compiler must be installed.

### Step 1: Clone the repository
Just click on the "Clone or Download" button at the top of this page and unzip the whole package in a folder of your choice.

### Step 2: Install all the dependencies
Then, open a shell (not python prompt!), change directory to the TagLab main directory and run:

```
python3 install.py
```
or, on Windows:

```
python.exe install.py
```

The script will automatically install the remaining libraries required by TagLab and download the network weights.
If NVIDIA CUDA Toolkit is not supported by your machine, the script will ask to install the cpu version.
You can bypass this step and force to install the cpu version directly by running
```
python3 install.py cpu
```
or, on Windows:

```
python.exe install.py cpu
```

### Step 3: Run
Just start `TagLab.py` from a command shell or your preferred Python IDE.

From a command shell simply write:

```
python3 taglab.py
```
or, on Windows:

```
python.exe taglab.py```
```

To test if TagLab works correctly, try to open the sample project available in the `projects` folder.

## Updating TagLab

If you already installed TagLab and you need to update to a new version, you can just run the `update.py` script:

```
python3 update.py
```
or, on Windows:

```
python.exe update.py```
```

The script will automatically update TagLab to the newest version available in this repository.

### Updating from 2.0

If you are updating TagLab from 2.0 version, in order to download also the new networks, please run the `update.py` script twice:

```
python3 update.py
python3 update.py
```
