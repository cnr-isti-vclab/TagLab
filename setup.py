import platform
import sys
import os

osused = platform.system()

#manage pythorch
nvcc_version = ''

stream = os.popen('nvcc --version')
output = stream.read()
pos = output.find('release')
cont = True
if pos >= 0:
    pos+=8
    nvcc_version = output[pos:pos+4 ]
    print('Found NVCC version: ' + nvcc_version)
else:
    print('WARNING:  NVCC not found.')

torch_package = 'torch==1.5.1'
torchvision_package = 'torchvision==0.6.1'

if '9.2' in nvcc_version:
    nvcc_version = '9.2'
    print('Torch for CUDA 9.2')
    torch_package+='+cu92'
    torchvision_package+='+cu92'
elif nvcc_version == '10.1':
    print('Torch for CUDA 10.1')
    torch_package+='+cu101'
    torchvision_package+='+cu101'
elif nvcc_version == '10.2':
    print('Torch for CUDA 10.2')
else:
    print('WARNING: NVCC version not supported by pythorch. Default PyTorch will be installed...')

#manage gdal
gdal_version = ''

if osused == 'Linux':
    import subprocess
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc == 0:
        gdal_version=output
    else:
        print('WARNING: GDAL lib not installed correctly.')
        print('"gdal-config --version" exit code: ' + str(rc))
    

gdal_package = 'gdal'
if gdal_version != '':
    gdal_package+= '==' + gdal_version 

#build coraline
if osused != 'Windows':
    try:
        out = subprocess.check_output(['cmake', '--version'])
        os.chdir('coraline')
        result = subprocess.getstatusoutput('cmake .')
        if result[0] == 0:
            result = subprocess.getstatusoutput('make')
            if result[0] == 0:
                print('Coraline built correctly.')
                os.chdir('..')
            else:
                print('WARNING: Error while building Coraline library.')
        else:
            print('WARNING: Error while configuring Coraline library.')
    except OSError:
        print('WARNING: cmake not found. Coraline library cannot be compiled.')

# requirements needed by TagLab
install_requires = [
    'wheel', 
    'pyqt5',
    'scikit-image',
    'scikit-learn',
    'pandas',
    'opencv-python',
    'matplotlib',
    'albumentations',
    'shapely'
]

#installing all the packages
for package in install_requires:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

#installing torch, gdal and rasterio

#torch
subprocess.check_call([sys.executable, "-m", "pip", "install", torch_package, '-f https://download.pytorch.org/whl/torch_stable.html'])
subprocess.check_call([sys.executable, "-m", "pip", "install", torchvision_package, '-f https://download.pytorch.org/whl/torch_stable.html'])

#gdal and rasterio
if osused != 'Windows':
    subprocess.check_call([sys.executable, "-m", "pip", "install", gdal_package])
    subprocess.check_call([sys.executable, "-m", "pip", "install", 'rasterio'])
