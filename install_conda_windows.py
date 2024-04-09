import os
import re
import sys
import shutil
import platform
import subprocess
from pathlib import Path
import urllib.request
import importlib.util as importutil

# ----------------------------------------------
# OS
# ----------------------------------------------
osused = platform.system()

if osused != 'Windows':
    raise Exception("This install script is only for Windows")

# ----------------------------------------------
# Conda
# ----------------------------------------------
# Need conda to install NVCC if it isn't already
console_output = subprocess.getstatusoutput('conda --version')

# Returned 1; conda not installed
if console_output[0]:
    raise Exception("This install script is only for Windows with Conda already installed")

conda_exe = shutil.which('conda')

# ----------------------------------------------
# Python version
# ----------------------------------------------
python_v = f"{sys.version_info[0]}{sys.version_info[1]}"
python_sub_v = int(sys.version_info[1])

# check python version
if python_sub_v < 8 or python_sub_v > 10:
    raise Exception(f"Python 3.{python_sub_v} not supported. "
                    f"Please see https://github.com/cnr-isti-vclab/TagLab/wiki/Install-TagLab")

# ----------------------------------------------
# Pytorch version
# ----------------------------------------------
something_wrong_with_nvcc = False
flag_install_pytorch_cpu = False
nvcc_version = ''
torch_package = 'torch'
torchvision_package = 'torchvision'
torch_extra_argument1 = ''
torch_extra_argument2 = ''

# If the user wants to install CPU torch
if len(sys.argv) == 2 and sys.argv[1] == 'cpu':
    flag_install_pytorch_cpu = True

# If user wants to install GPU torch
elif not flag_install_pytorch_cpu:

    # Get the version of NVCC
    console_output = subprocess.getstatusoutput('nvcc --version')

    # Returned 1; NVCC not installed, install 11.8 cuda nvcc
    if console_output[0]:

        try:
            # Command for installing cuda nvcc
            conda_command = [conda_exe, "install", "-c", f"nvidia/label/cuda-11.8.0", "cuda-nvcc", "-y"]

            # Run the conda command
            subprocess.run(conda_command, check=True)

            # Set the nvcc version
            nvcc_version = "11.8.0"

        except Exception as e:
            print("There was an issue installing CUDA NVCC with conda")
            something_wrong_with_nvcc = True

    else:
        # Search for the pattern in the text
        pattern = re.compile(r'release (\d+\.\d+),')
        match = pattern.search(console_output[1])

        # Extract the version if a match is found
        if match:
            nvcc_version = match.group(1)
            print(f"NVCC version: {nvcc_version}")
        else:
            print(f"NVCC version could not be found, exiting")
            something_wrong_with_nvcc = True

    # Install pytorch using nvcc version
    if '9.2' in nvcc_version:
        nvcc_version = '9.2'
        print('Torch 1.7.1 for CUDA 9.2')
        torch_package += '==1.7.1+cu92'
        torchvision_package += '==0.8.2+cu92'
        torch_extra_argument1 = '-f'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/torch_stable.html'
    elif nvcc_version == '10.1':
        print('Torch 1.7.1 for CUDA 10.1')
        torch_package += '==1.7.1+cu101'
        torchvision_package += '==0.8.2+cu101'
        torch_extra_argument1 = '-f'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/torch_stable.html'
    elif nvcc_version == '10.2':
        print('Torch 1.11.0 for CUDA 10.2')
        torch_package += '==1.11.0+cu102'
        torchvision_package += '==0.12.0+cu102'
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu102'
    elif '11.0' in nvcc_version:
        print('Torch 1.7.1 for CUDA 11.0')
        torch_package += '==1.7.1+cu110'
        torchvision_package += '0.8.2+cu110'
        torch_extra_argument1 = '-f'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/torch_stable.html'
    elif '11.1' in nvcc_version:
        print('Torch 1.8.0 for CUDA 11.1')
        torch_package += '==1.8.0+cu111'
        torchvision_package += '==0.9.0+cu111'
        torch_extra_argument1 = '-f'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/torch_stable.html'
    elif '11.3' in nvcc_version:
        print('Torch 1.12.1 for CUDA 11.3')
        torch_package += '==1.12.1+cu113'
        torchvision_package += '==0.13.1+cu113'
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu113'
    elif '11.6' in nvcc_version:
        print('Torch 1.13.1 for CUDA 11.6')
        torch_package += '==1.13.1+cu116'
        torchvision_package += '==0.14.1+cu116'
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu116'
    elif '11.7' in nvcc_version:
        print('Torch 1.13.1 for CUDA 11.7')
        torch_package += '==1.13.1+cu117'
        torchvision_package += '==0.14.1+cu117'
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu117'
    elif '11.8' in nvcc_version:
        print("Torch 2.0.0 for CUDA 11.8")
        torch_package += '==2.0.0+cu118'
        torchvision_package += '==0.15.1+cu118'
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu118'
    elif '12.1' in nvcc_version or (nvcc_version and not something_wrong_with_nvcc):
        print("Torch 2.1.0 for CUDA")
        torch_extra_argument1 = '--index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu121'

    # if the user tried to run the installer but there were issues on finding a supported
    if something_wrong_with_nvcc == True and flag_install_pytorch_cpu == False:
        ans = input('Something is wrong with NVCC. '
                    'Do you want to install the CPU version of pytorch? [Y/n]')
        if ans.lower().strip() == "y":
            flag_install_pytorch_cpu = True
        else:
            raise Exception('Installation aborted. '
                            'Install a proper NVCC version or set the pytorch CPU version.')

# The user choose to install for CPU
if flag_install_pytorch_cpu == True:
    print('Torch will be installed in its CPU version.')
    torch_extra_argument1 = '--extra-index-url'
    torch_extra_argument2 = 'https://download.pytorch.org/whl/cpu'

# ----------------------------------------------
# Other dependencies
# ----------------------------------------------
install_requires = [
    'msvc-runtime',
    'wheel',
    'pyqt5',
    'scikit-image',
    'scikit-learn',
    'pandas',
    'opencv-python',
    'matplotlib',
    'albumentations',
    'shapely',
    'numpy',
    'qhoptim',

    # CoralNet Toolbox
    'Requests',
    'beautifulsoup4',
    'selenium',
    'webdriver_manager',
]

if python_sub_v < 9:
    install_requires.append('pycocotools-windows')
else:
    # Jesus, take the wheel
    install_requires.append('pycocotools')

# Installing all the packages
for package in install_requires:

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    except Exception as e:
        print(f"There was an issue installing the necessary packages.\n{e}")
        print(f"The error came from installing {package}")
        print(f"If you're not already, please try using a conda environment with python 3.8")
        sys.exit(1)


# Setting Torch, Torchvision versions
list_args = [sys.executable, "-m", "pip", "install", torch_package, torchvision_package]
if torch_extra_argument1 != "":
    list_args.extend([torch_extra_argument1, torch_extra_argument2])

# Installing Torch, Torchvision
subprocess.check_call(list_args)

# ----------------------------------------------
# GDAL Version
# ----------------------------------------------
# Locally stored wheels
base_url = './packages/'

# Compute gdal urls download
gdal_win_version = '3.4.3'
filename_gdal = 'gdal-' + gdal_win_version + '-cp' + python_v + '-cp' + python_v
filename_gdal += '-win_amd64.whl'
base_url_gdal = base_url + filename_gdal

if not os.path.exists(base_url_gdal):
    raise Exception(f"Could not find {base_url_gdal}; aborting")

# See if rasterio and gdal are already installed
try:
    gdal_is_installed = importutil.find_spec("osgeo.gdal")
except:
    gdal_is_installed = None

if gdal_is_installed is not None:
    import osgeo.gdal

    print("GDAL ", osgeo.gdal.__version__, " is installed. "
          "Version ", gdal_win_version, "is required.")
else:
    # retrieve GDAL from packages
    print('GET GDAL FROM URL: ' + base_url_gdal)

    # install gdal from packages
    subprocess.check_call([sys.executable, "-m", "pip", "install", base_url_gdal])

# ----------------------------------------------
# Rasterio Version
# ----------------------------------------------
# Compute rasterio urls download
rasterio_win_version = '1.2.10'
filename_rasterio = 'rasterio-' + rasterio_win_version + '-cp' + python_v + '-cp' + python_v
filename_rasterio += '-win_amd64.whl'
base_url_rasterio = base_url + filename_rasterio

if not os.path.exists(base_url_rasterio):
    raise Exception(f"Could not find {base_url_rasterio}; aborting")

try:
    rasterio_is_installed = importutil.find_spec("rasterio")
except:
    rasterio_is_installed = None

# if so, check versions
if rasterio_is_installed is not None:
    import rasterio

    print("RASTERIO ", rasterio.__version__, " is installed. "
          "Version ", rasterio_win_version, " is required.")
else:
    # retrieve rasterio from packages
    print('GET RASTERIO FROM URL: ' + base_url_rasterio)

    # install rasterio
    subprocess.check_call([sys.executable, "-m", "pip", "install", base_url_rasterio])

# ----------------------------------------------
# Model Weights
# ----------------------------------------------
print('Downloading networks...')
this_directory = os.path.abspath(os.path.dirname(__file__))

# ---------------
# TagLab Weights
# ---------------
base_url = 'http://taglab.isti.cnr.it/models/'
net_file_names = ['dextr_corals.pth',
                  'deeplab-resnet.pth.tar',
                  'ritm_corals.pth',
                  'pocillopora.net',
                  'porites.net',
                  'pocillopora_porite_montipora.net']

for net_name in net_file_names:
    filename_dextr_corals = 'dextr_corals.pth'
    net_file = Path('models/' + net_name)
    if not net_file.is_file():  # if file not exists
        try:
            url_dextr = base_url + net_name
            print('Downloading ' + url_dextr + '...')
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url_dextr, 'models/' + net_name)
        except:
            raise Exception("Cannot download " + net_name + ".")
    else:
        print(net_name + ' already exists.')

print("Done.")