from distutils.core import setup
import platform
import sys
import os

osused = platform.system()

#manage pythorch
nvcc_version = ''

stream = os.popen('nvcc --version')
output = stream.read()
pos = output.find('release')
if pos >= 0:
    pos+=8
    nvcc_version = output[pos:pos+4 ]
    
print('nvcc_version: ' + nvcc_version)

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
    print('WARNING: NVIDIA CUDA not installed or NVCC version not supported by pythorch.')

#manage gdal
gdal_version = ''

if osused == 'Linux':
    print('Installing gdal...')
    import osgeo.gdal
    gdal_version=osgeo.gdal.__version__
    

gdal_package = 'gdal'
if gdal_version != '':
    gdal_package+= '==' + gdal_version 

#utilities for build coraline
import pathlib

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as build_ext_orig

class CMakeExtension(Extension):

    def __init__(self, name):
        # don't invoke the original build_ext for this special extension
        super().__init__(name, sources=[])


class build_ext(build_ext_orig):

    def run(self):
        for ext in self.extensions:
            self.build_cmake(ext)
        super().run()

    def build_cmake(self, ext):
        cwd = pathlib.Path().absolute()

        # these dirs will be created in build_py, so if you don't have
        # any python sources to bundle, the dirs will be missing
        build_temp = pathlib.Path(self.build_temp)
        build_temp.mkdir(parents=True, exist_ok=True)
        extdir = pathlib.Path(self.get_ext_fullpath(ext.name))
        extdir.mkdir(parents=True, exist_ok=True)

        # example of cmake args
        config = 'Debug' if self.debug else 'Release'
        cmake_args = [
            '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + str(extdir.parent.absolute()),
            '-DCMAKE_BUILD_TYPE=' + config
        ]

        # example of build args
        build_args = [
            '--config', config,
            '--', '-j4'
        ]

        os.chdir(str(build_temp))
        self.spawn(['cmake', str(cwd)] + cmake_args)
        if not self.dry_run:
            self.spawn(['cmake', '--build', '.'] + build_args)
        # Troubleshooting: if fail on line above then delete all possible 
        # temporary CMake files including "CMakeCache.txt" in top level dir.
        os.chdir(str(cwd))
        
if osused != 'Windows':
    ext_modules=[CMakeExtension('coraline')]
else:
    ext_modules=[] #already built on windows

# read the contents of README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# requirements needed by piè
install_requires = [
    'wheel', 
    torch_package, 
    torchvision_package,
    'pyqt5',
    'scikit-image',
    'scikit-learn',
    'pandas',
    'opencv-python',
    'matplotlib',
    'albumentations',
    'rasterio',
    gdal_package,
    'shapely'
]
    
dependency_links = [
    'https://download.pytorch.org/whl/torch_stable.html'
]

setup(
    # Application name:
    name="TagLab",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Gaia Pavoni",
    author_email="name@addr.ess",

    # Packages
    packages=[],

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="http://pypi.python.org/pypi/MyApplication_v010/",

    #
    # license="LICENSE.txt",
    description="Useful towel-related stuff.",
    
    long_description=long_description,
    long_description_content_type='text/markdown',

    # Dependent packages (distributions)
    dependency_links=dependency_links,
    install_requires=install_requires,
    ext_modules=ext_modules,
    cmdclass={
        'build_ext': build_ext,
    }
)
