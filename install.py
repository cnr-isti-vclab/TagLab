import platform
import sys
import os
import subprocess

osused = platform.system()
if osused != 'Linux' and osused != 'Windows' and osused != 'Darwin':
    raise Exception("Operative System not supported")

# check python version
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 6):
    raise Exception("Must be using Python >= 3.6\nInstallation aborted.")

# manage thorch
nvcc_version = ''

result = subprocess.getstatusoutput('nvcc --version')
output = result[1]
rc = result[0]
if rc == 0:
    pos = output.find('release')
    cont = True
    if pos >= 0:
        pos += 8
        nvcc_version = output[pos:pos+4]
        print('Found NVCC version: ' + nvcc_version)
    else:
        raise Exception('Could not read NVCC version.\nInstallation aborted.')
else:
    raise Exception('NVCC not found. Please install NVidia CUDA first.\nInstallation aborted.')

torch_package = 'torch==1.5.1'
torchvision_package = 'torchvision==0.6.1'

if '9.2' in nvcc_version:
    nvcc_version = '9.2'
    print('Torch for CUDA 9.2')
    torch_package += '+cu92'
    torchvision_package += '+cu92'
elif nvcc_version == '10.1':
    print('Torch for CUDA 10.1')
    torch_package += '+cu101'
    torchvision_package += '+cu101'
elif nvcc_version == '10.2':
    print('Torch for CUDA 10.2')
else:
    raise Exception('NVCC version not supported by pythorch.\nInstallation aborted.')

# manage gdal
gdal_version = ''

if osused == 'Linux':
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc != 0:
        print('Trying to install libgdal-dev...')
        from subprocess import STDOUT, check_call
        import os
        try:
            check_call(['sudo', 'apt-get', 'install', '-y', 'libgdal-dev'],
                       stdout=open(os.devnull, 'wb'), stderr=STDOUT)
        except:
            raise Exception('Impossible to install libgdal-dev. Please install manually libgdal-dev before running '
                            'this script.\nInstallation aborted.')
        result = subprocess.getstatusoutput('gdal-config --version')
        output = result[1]
        rc = result[0]
    if rc == 0:
        gdal_version = output
        print('GDAL version installed: ' + output)
    else:
        raise Exception('Impossible to access to gdal-config binary.\nInstallation aborted.')
elif osused == 'Darwin':
    print('TODO: Manage installagion of gdal from MacOS')
    raise Exception('TODO Manage installagion of gdal from MacOS')
    

gdal_package = 'gdal==' + gdal_version

# build coraline
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
                raise Exception('Error while building Coraline library.\nInstallation aborted.')
        else:
            raise Exception('Error while configuring Coraline library.\nInstallation aborted.')
    except OSError:
        raise Exception('Cmake not found. Coraline library cannot be compiled. Please install cmake '
                        'first.\nInstallation aborted.')

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

# installing all the packages
for package in install_requires:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# installing torch, gdal and rasterio

# torch
subprocess.check_call([sys.executable, "-m", "pip", "install", torch_package,
                       '-f https://download.pytorch.org/whl/torch_stable.html'])
subprocess.check_call([sys.executable, "-m", "pip", "install", torchvision_package,
                       '-f https://download.pytorch.org/whl/torch_stable.html'])

# gdal and rasterio

if osused != 'Windows':
    subprocess.check_call([sys.executable, "-m", "pip", "install", gdal_package])
    subprocess.check_call([sys.executable, "-m", "pip", "install", 'rasterio'])
else:
    base_url = 'http://taglab.isti.cnr.it/wheels/'
    pythonversion = str(sys.version_info[0]) + str(sys.version_info[1])
    # compute rasterio and gdal urls download
    filename_gdal = 'GDAL-3.1.2-cp' + pythonversion + '-cp' + pythonversion
    filename_rasterio = 'rasterio-1.1.5-cp' + pythonversion + '-cp' + pythonversion
    if sys.version_info[1] < 8:
        filename_gdal += 'm'
        filename_rasterio += 'm'
    filename_gdal += '-win_amd64.whl'
    filename_rasterio += '-win_amd64.whl'
    base_url_gdal = base_url + filename_gdal
    base_url_rastetio = base_url + filename_rasterio

    print('URL GDAL: ' + base_url_gdal)

    # download gdal and rasterio
    from os import path
    import urllib.request

    this_directory = path.abspath(path.dirname(__file__))
    try:
        slib = 'GDAL'
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(base_url_gdal, this_directory + '/' + filename_gdal)
        slib = 'Rasterio'
        urllib.request.urlretrieve(base_url_rastetio, this_directory + '/' + filename_rasterio)
    except:
        raise Exception("Cannot download " + slib + ".")

    # install gdal and rasterio
    subprocess.check_call([sys.executable, "-m", "pip", "install", filename_gdal])
    subprocess.check_call([sys.executable, "-m", "pip", "install", filename_rasterio])

    #delete wheel files
    os.remove(this_directory + '/' + filename_gdal)
    os.remove(this_directory + '/' + filename_rasterio)
    
# download models
base_url = 'http://taglab.isti.cnr.it/models/'
from os import path
import urllib.request
this_directory = path.abspath(path.dirname(__file__))

filename_dextr_corals = 'dextr_corals.pth'
try:
    url_dextr = base_url + filename_dextr_corals
    print('Downloading ' + url_dextr + '...')
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url_dextr, 'models/' + filename_dextr_corals)
except:
    raise Exception("Cannot download " + filename_dextr_corals + ".")
    
filename_deeplab = 'deeplab-resnet.pth.tar'
try:
    url_deeplab = base_url + filename_deeplab
    print('Downloading ' + url_deeplab + '...')
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url_deeplab, this_directory + '/models/' + filename_deeplab)
except:
    raise Exception("Cannot download " + filename_deeplab + ".")

