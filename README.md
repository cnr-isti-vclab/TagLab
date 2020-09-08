### TagLab: an image segmentation tool oriented to marine data analysis

TagLab was created to support the activity of annotation and extraction of statistical data from ortho-maps of benthic communities. The tool includes different types of CNN-based segmentation networks specially trained for agnostic (relative only to contours) or semantic (also related to species) recognition of corals. TagLab is an ongoing project of the Visual Computing Lab http://vcg.isti.cnr.it/.

![ScreenShot](screenshot.jpg)

  
### Interaction:
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


### Installing TagLab
#### Step 0: Requirements
Taglab relies mainly on __*CUDA*__ and __*Python*__ . Be sure to install Python and the NVIDIA CUDA Toolkit before 
to install the other packages required. THe CUDA version supported are 9.2, 10.1 and 10.2. 
TagLab has been successfully tested with Python 3.6.x and Python 3.7.x. We report problems with Python 3.8.x.
On Linux, also __*cmake*__ and a C++ compiler must be installed.
 
#### Step 1: Clone the repository
Just click on the "Clone or Download" button at the top of this page and unzip the whole package in a folder of your choice. 

#### Step 2: Install dependencies
Open a python prompt and start `install.py`. The script will automatically install the remaining libraries required by TagLab and download the network weights.

#### Step 3: Run
Open a python prompt and just start `TagLab.py`, the tool will start and you can try to open the sample that you can find in the `projects` folder. 
