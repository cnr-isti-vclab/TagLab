import platform
import sys
import os
import subprocess
from pathlib import Path

osused = platform.system()
if osused != 'Linux' and osused != 'Windows' and osused != 'Darwin':
    raise Exception("Operative System not supported")

# check python version
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and (sys.version_info[1] < 10)):
    raise Exception("Python " + str(sys.version_info[0]) + "." + str(sys.version_info[1]) + " not supported. Please see https://github.com/cnr-isti-vclab/TagLab/wiki/Install-TagLab")

# manage thorch

# define a dictionary that, for each nvcc version, contains the corresponding torch and torchvision version
# the key is the nvcc version, the value is a list of arguments to be passed to pip install

torch_cuda_versions = ['12.1', '11.8', '11.6']

torch_install_dict = None

win_torch_install_dict = {
    '11.6': ['torch==1.13.1+cu116', 'torchvision==0.14.1+cu116', '--extra-index-url' + 'https://download.pytorch.org/whl/cu116'],
    '11.8': ['torch==2.3.1', 'torchvision==0.18.1', '--index-url', 'https://download.pytorch.org/whl/cu118'],
    '12.1': ['torch==2.3.1', 'torchvision==0.18.1', '--index-url', 'https://download.pytorch.org/whl/cu121'],
    'cpu' : ['torch==2.3.1', 'torchvision==0.18.1'],
}

lin_torch_install_dict = {
    '11.6': ['torch==1.13.1+cu116', 'torchvision==0.14.1+cu116', '--extra-index-url' + 'https://download.pytorch.org/whl/cu116'],
    '11.8': ['torch==2.3.1', 'torchvision==0.18.1', '--index-url', 'https://download.pytorch.org/whl/cu118'],
    '12.1': ['torch==2.3.1', 'torchvision==0.18.1'],
    'cpu' : ['torch==2.3.1', 'torchvision==0.18.1', '--index-url', 'https://download.pytorch.org/whl/cpu'],
}

mac_torch_install_dict = {
    'cpu' : ['torch==2.3.1', 'torchvision==0.18.1'],
}

if osused == 'Windows':
    torch_install_dict = win_torch_install_dict
elif osused == 'Linux':
    torch_install_dict = lin_torch_install_dict
elif osused == 'Darwin':
    torch_install_dict = mac_torch_install_dict

something_wrong_with_cuda = False
flag_install_pythorch_cpu = False
nvcc_version = ''
torch_package = ''
torchvision_package = ''
torch_extra_argument1 = ''
torch_extra_argument2 = ''

# if the user wants to install cpu torch
if len(sys.argv)==2 and sys.argv[1]=='cpu':
    flag_install_pythorch_cpu = True


# get cuda version
cuda_version = ''

if osused == 'Darwin':
    flag_install_pythorch_cpu = True
    print('NVCC not supported on MacOS. Installing cpu version automatically...')
elif flag_install_pythorch_cpu == False:
    result = subprocess.getstatusoutput('nvidia-smi')
    output = result[1]
    rc = result[0]
    if rc == 0:
        pos = output.find('CUDA Version:')
        if pos >= 0:
            pos += 13
            cuda_version = output[pos:pos+6]
            print('Found CUDA version: ' + cuda_version)
        else:
            raise Exception('Could not read CUDA version.\nInstallation aborted.')
    else:
        print('Impossible to run "nvidia-smi" command. CUDA seems to be not installed.')
        something_wrong_with_cuda = True # remember that we had issues on finding nvcc

    # get the float number of the cuda version
    n_cuda_version = float(cuda_version)

    torch_cuda_version = ''

    # for each version of cuda in torch_cuda_versions
    for version in torch_cuda_versions:
        if n_cuda_version >= float(version):
            print ('Using Torch cuda version: ' + version)
            torch_cuda_version = version
            break

    if torch_cuda_version == '':
        print('No supported version of Torch for CUDA ' + cuda_version + '.')
        something_wrong_with_cuda = True

    # set the torch and torchvision packages
    if flag_install_pythorch_cpu == False:
        torch_package = torch_install_dict[torch_cuda_version][0]
        torchvision_package = torch_install_dict[torch_cuda_version][1]
        if len(torch_install_dict[torch_cuda_version]) > 2:
            torch_extra_argument1 = torch_install_dict[torch_cuda_version][2]
            torch_extra_argument2 = torch_install_dict[torch_cuda_version][3]

    # if the user tried to run the installer but there were issues on finding a supported
    if something_wrong_with_cuda == True and flag_install_pythorch_cpu == False:
        ans = input('Something is wrong with Cuda. Do you want to install the CPU version of pythorch? [Y/n]')
        if ans == "Y":
            flag_install_pythorch_cpu = True
        else:
            raise Exception('Installation aborted. Install a proper Cuda version or set the pythorch CPU version.')


# somewhere before, this flag has been set to True and the user choose to install the cpu torch version
if flag_install_pythorch_cpu==True:
    print('Torch will be installed in its CPU version.')
    torch_package = torch_install_dict['cpu'][0]
    torchvision_package = torch_install_dict['cpu'][1]
    if len(torch_install_dict['cpu']) > 2:
        torch_extra_argument1 = torch_install_dict['cpu'][2]
        torch_extra_argument2 = torch_install_dict['cpu'][3]

# manage gdal
gdal_version = ''

if osused == 'Linux' or osused == 'Darwin':
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc != 0:
        if osused == 'Linux':
            print('Trying to install libxcb-xinerama0...')
            from subprocess import STDOUT, check_call
            import os
            try:
                check_call(['sudo', 'apt-get', 'install', '-y', 'libxcb-xinerama0'],
                   stdout=open(os.devnull, 'wb'), stderr=STDOUT)
            except:
                print('Impossible to install libxcb-xinerama0. If TagLab does not start, please install manually libxcb-xinerama0.')

            print('Trying to install gdal...')
            try:
                check_call(['sudo', 'apt-get', 'install', '-y', 'libgdal-dev'],
                        stdout=open(os.devnull, 'wb'), stderr=STDOUT)
            except:
                raise Exception('Impossible to install libgdal-dev. Please install manually libgdal-dev before running '
                                'this script.\nInstallation aborted.')
            result = subprocess.getstatusoutput('gdal-config --version')
            output = result[1]
            rc = result[0]
        elif osused == 'Darwin':
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
    'pycocotools',
    'qhoptim',

    # CoralNet Toolbox
    'Requests',
    'beautifulsoup4',
    'selenium',
    'webdriver_manager',

    # SAM
    'segment-anything',

    #forcing numpy 1.24.2 version
    'numpy==1.24.4',
]

# if on windows, first install the msvc runtime
if osused == 'Windows':
    install_requires.insert(0, 'msvc-runtime')

# installing all the packages
for package in install_requires:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# installing torch, gdal and rasterio

# torch and torchvision
list_args = [sys.executable, "-m", "pip", "install", torch_package, torchvision_package]
if torch_extra_argument1 != "":
    list_args.extend([torch_extra_argument1, torch_extra_argument2])

subprocess.check_call(list_args)

# gdal and rasterio

if osused != 'Windows':
    subprocess.check_call([sys.executable, "-m", "pip", "install", gdal_package])
    subprocess.check_call([sys.executable, "-m", "pip", "install", 'rasterio'])
else:
    base_url = 'https://github.com/cgohlke/geospatial-wheels/releases/download/v2024.9.22/' # GDAL-3.9.2-cp310-cp310-win32.whl
    pythonversion = str(sys.version_info[0]) + str(sys.version_info[1])
    # compute rasterio and gdal urls download
    rasterio_win_version = '1.3.11'
    gdal_win_version = '3.9.2'
    filename_gdal = 'gdal-' + gdal_win_version + '-cp' + pythonversion + '-cp' + pythonversion
    filename_rasterio = 'rasterio-' + rasterio_win_version +'-cp' + pythonversion + '-cp' + pythonversion
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
                  'pocillopora.net', 'porites.net', 'pocillopora_porite_montipora.net',
                  'sam_vit_h_4b8939.pth']

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
