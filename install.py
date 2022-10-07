import platform
import sys
import os
import subprocess
from pathlib import Path

osused = platform.system()
if osused != 'Linux' and osused != 'Windows' and osused != 'Darwin':
    raise Exception("Operative System not supported")

# check python version
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
    raise Exception("Must be using Python >= 3.7\nInstallation aborted.")

# manage thorch
something_wrong_with_nvcc = False
flag_install_pythorch_cpu = False
nvcc_version = ''
torch_package = 'torch'
torchvision_package = 'torchvision'
torch_extra_argument1 = ''
torch_extra_argument2 = ''

# if the user wants to install cpu torch
if len(sys.argv)==2 and sys.argv[1]=='cpu':
    flag_install_pythorch_cpu = True

# get nvcc version

if osused == 'Darwin':
    flag_install_pythorch_cpu = True
    print('NVCC not supported on MacOS. Installing cpu version automatically...')
elif flag_install_pythorch_cpu == False:
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
        print('Impossible to run "nvcc --version" command. CUDA seems to be not installed.')
        something_wrong_with_nvcc = True # remember that we had issues on finding nvcc


    # get nvcc version
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
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu113'
    elif '11.6' in nvcc_version:
        print('Torch 1.12.1 for CUDA 11.6')
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cu116'
    elif something_wrong_with_nvcc==False:
        # nvcc is installed, but some version that is not supported by torch
        print('nvcc version installed not supported by pytorch!!')
        something_wrong_with_nvcc = True # remember that we had issues on finding nvcc

    # if the user tried to run the installer but there were issues on finding a supported
    if something_wrong_with_nvcc == True and flag_install_pythorch_cpu == False:
        ans = input('Something is wrong with NVCC. Do you want to install the CPU version of pythorch? [Y/n]')
        if ans == "Y":
            flag_install_pythorch_cpu = True
        else:
            raise Exception('Installation aborted. Install a proper NVCC version or set the pythorch CPU version.')


# somewhere before, this flag has been set to True and the user choose to install the cpu torch version
if flag_install_pythorch_cpu==True:
    print('Torch will be installed in its CPU version.')
    if osused != 'Darwin': # for macos, the DEFAULT is cpu, therefore we don't need the extra arguments
        torch_extra_argument1 = '--extra-index-url'
        torch_extra_argument2 = 'https://download.pytorch.org/whl/cpu'

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
    print('Trying to install libxcb-xinerama0...')
    from subprocess import STDOUT, check_call
    import os
    try:
        check_call(['sudo', 'apt-get', 'install', '-y', 'libxcb-xinerama0'],
                   stdout=open(os.devnull, 'wb'), stderr=STDOUT)
    except:
        print('Impossible to install libxcb-xinerama0. If TagLab does not start, please install manually libxcb-xinerama0.')

elif osused == 'Darwin':
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc != 0:
        print('Trying to install gdal...')
        from subprocess import STDOUT, check_call
        import os
        try:
            check_call(['brew', 'install', 'gdal'],
                       stdout=open(os.devnull, 'wb'), stderr=STDOUT)
        except:
            raise Exception('Impossible to install gdal through homebrew. Please install manually gdal before running '
                            'this script.\nInstallation aborted.')
        result = subprocess.getstatusoutput('gdal-config --version')
        output = result[1]
        rc = result[0]
    if rc == 0:
        gdal_version = output
        print('GDAL version installed: ' + output)
    else:
        raise Exception('Impossible to access to gdal-config binary.\nInstallation aborted.')

gdal_package = 'gdal==' + gdal_version

# build coraline
if osused != 'Windows':
    try:
        out = subprocess.check_output(['cmake', '--version'])
        if out[0] != 0:
            if osused == 'Darwin':
                print('Trying to install cmake...')
                from subprocess import STDOUT, check_call
                import os
                try:
                    check_call(['brew', 'install', 'cmake'],
                               stdout=open(os.devnull, 'wb'), stderr=STDOUT)
                except:
                    raise Exception('Impossible to install cmake through homebrew. Please install manually cmake before running '
                                    'this script.\nInstallation aborted.')
            elif osused == 'Linux':
                print('Trying to install cmake...')
                from subprocess import STDOUT, check_call
                import os
                try:
                    check_call(['sudo', 'apt-get', 'install', '-y', 'cmake'],
                               stdout=open(os.devnull, 'wb'), stderr=STDOUT)
                except:
                    raise Exception('Impossible to install cmake. Please install manually cmake before running '
                                    'this script.\nInstallation aborted.')
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
    'shapely',
    'pycocotools'
]

# installing all the packages
for package in install_requires:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# installing torch, gdal and rasterio

# torch and torchvision
subprocess.check_call([sys.executable, "-m", "pip", "install", torch_package,
                       torchvision_package, torch_extra_argument1,
                       torch_extra_argument2])

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

# check for other networks
print('Downloading networks...')
base_url = 'http://taglab.isti.cnr.it/models/'
from os import path
import urllib.request
this_directory = path.abspath(path.dirname(__file__))
net_file_names = ['dextr_corals.pth', 'deeplab-resnet.pth.tar', 'ritm_corals.pth',
                  'pocillopora.net', 'porites.net', 'pocillopora_porite_montipora.net']

for net_name in net_file_names:
    filename_dextr_corals = 'dextr_corals.pth'
    net_file = Path('models/' + net_name)
    if not net_file.is_file(): #if file not exists
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
