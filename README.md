### TagLab: an image segmentation tool oriented to marine data analysis

TagLab was created to support the activity of annotation and extraction of statistical data from ortho-maps of benthic communities. The tool includes different types of CNN-based segmentation networks specially trained for agnostic (relative only to contours) or semantic (also related to species) recognition of corals. TagLab is an ongoing project of the Visual Computing Lab http://vcg.isti.cnr.it/.

![ScreenShot](screenshot.jpg)

  
### Interaction:
TagLab allows to :

- zoom and navigate a large map using a Map viewer
       -zoom/ mouse wheel
      - pan/ 'move' tool  selected + left button
       -with every other tool selected the pan is activated with ctrl + left button
- segment coral instances using the Deep Extreme Cut network fine-tuned on coral images.

Deep Extreme Cut original code : https://github.com/scaelles/DEXTR-PyTorch/

- assign a class with the 'Assign class' tool. Area and perimeter are now displayed in pixels (the scale can be added to transform measures in mm) in the segmentation info panel on the right.
- simultaneously turn off the visibility of one or more classes, (ctrl + left button/disable all but the selected, shift + left button, inverse operation), change the class transparency using the above slider.
- edit the incorrect edges with the 'Edit Border' tool.
- Draw coral internal cracks with the 'Create Crack' tool.
- Perform the boolean operation between labels: 'Merge Overlapped Labels', 'Divide Label', 'Subtract Label' (right button panel)
- make freehand measurements or measure the distance between centroids (Ruler tool).
- save the annotations (as polygons) and import them into a new project (Save Annotation, Load Annotation)
- Export a .csv file table containing the data of each coral colony.
- Export a .jpg file of a black background with totally opaque labels.


### Installing TagLab
#### Step 0: Requirements
Taglab relies mainly on __*CUDA*__ and __*Python*__ . Be sure to install them before to install the other packages required. THe CUDA version supported are 9.2, 10.1 and 10.2. TagLab has been successfully tested with Python 3.6.x and Python 3.7.x. We report problems with Python 3.8.x.

The simplest way to install the required packages is through the Python package manager (pip): 

| Package    | Command |
|-----------|----|
|  (*) pytorch 1.0+  | `pip install torch==1.5.1 torchvision==0.6.1 -f https://download.pytorch.org/whl/torch_stable.html `|
|  pyqt5 5.13+|  `pip install pyqt5 ` |
|  scikit-image  |  `pip install scikit-image `|
|  scikit-learn  | `pip install scikit-learn `|
|  pandas  | `pip install pandas `|
|  opencv-python | `pip install opencv-python `|
|  matplotlib  | `pip install matplotlib `|
|  albumentations  | `pip install albumentations `|


(*) The right command to install pytorch depends on the version of CUDA installed on your system. Go on the **[Get Started](https://pytorch.org/get-started/locally)** web page of the Pytorch web site, select your system, select Pip, and select your CUDA version to get the command to launch.

#### Step 1: Clone the repository
Just click on the "Clone or Download" button at the top of this page and unzip the whole package in a folder of your choice. 

#### Step 2: Download the network weights
TagLab uses a retrained _dextr_ network for the four-click segmentation; the file with the weights is not included in the git repository for its size and have to be downloaded from this **[link](http://vcg.isti.cnr.it/~cignoni/TagLab/dextr_corals.pth  )**; the downloaded `dextr_corals.pth` file must be placed in the `models` folder of the repository downloaded at the previous steps


#### Step 3: Run
Open a python prompt and just start `TagLab.py`, the tool will start and you can try to open the sample that you can find in the `projects` folder. 

 
### Planned features : late 2019

- Optimization of the EditBorder tool (currently slow on large instances).
- Project initialization Interface (Map, scale, Folder, Global Coordinates).
- Management of different layers (comparison different years surveys).
- Weights of a more accurate Deep Extreme Segmentation network.
- Possibility to manage the registration of colonies with dead portions.
- Addition of a Semantic Segmentation Network.
