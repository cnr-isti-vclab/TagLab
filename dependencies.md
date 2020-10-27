### Installing TagLab
#### Step 0: Requirements
Taglab relies mainly on __*CUDA*__ and __*Python*__ . Be sure to install Python and the NVIDIA CUDA Toolkit before 
to install the other packages required. THe CUDA version supported are 9.2, 10.1 and 10.2. 
TagLab has been successfully tested with Python 3.6.x and Python 3.7.x. We report problems with Python 3.8.x.

The simplest way to install the required packages is through the Python package manager (pip): 

| Package | Command |
|---------|---------|
|  (*) pytorch 1.5+ | `pip install torch==1.5.1 torchvision==0.6.1 -f https://download.pytorch.org/whl/torch_stable.html` |
|  pyqt5 5.15+ |  `pip install pyqt5` |
|  scikit-image  |  `pip install scikit-image` |
|  scikit-learn  | `pip install scikit-learn` |
|  pandas  | `pip install pandas` |
|  opencv-python | `pip install opencv-python` |
|  matplotlib  | `pip install matplotlib` |
|  albumentations  | `pip install albumentations` |
|  (**) rasterio 1.1.5+ | `pip install rasterio` |
|  (**) GDAL 3.1.2+ | `pip install gdal` | 


(*) The right command to install pytorch depends on the version of CUDA installed on your system. 
Go on the **[Get Started](https://pytorch.org/get-started/locally)** web page of the Pytorch web site, select your system, select Pip, and select your CUDA version to get the command to launch.

(**) On Windows these packages cannot be installed directly using *pip*. We recommend to install them by getting the 
unofficial binaries **[here](https://www.lfd.uci.edu/~gohlke/pythonlibs/)**. For example, if you are installing 
Taglab on a 64-bit Windows system with Python 3.6 you can download and install the `GDAL‑3.1.2‑cp36‑cp36m‑win_amd64.whl` 
wheel for GDAL and the `rasterio‑1.1.5‑cp36‑cp36m‑win_amd64.whl` wheel for Rasterio.