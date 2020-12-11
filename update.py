import platform
import sys
import os
import urllib.request
import tempfile
import zipfile
import shutil
import subprocess

#directories that will be replaced or merged during the update
to_merge_directories = ['models', 'sample']
to_replace_directories = ['coraline', 'docs', 'fonts', 'icons', 'source', '.github']
# note:
# - all the other directories present in the main directory will be left
# - the update may create other directories that are not listed here
# - all the files (non-directories) in the main directory are replaced.
# - Old version of 'config.json' will be saved as 'config.json.bak'

osused = platform.system()

github_repo = 'alemuntoni/TagLab/'
base_repo = 'https://github.com/' + github_repo
raw_link = 'https://raw.githubusercontent.com/' + github_repo + 'main/TAGLAB_VERSION'

# read offline version
f_off_version = open("TAGLAB_VERSION", "r")
taglab_offline_version = f_off_version.read()

print('Raw link: ' + raw_link)
f_online_version = urllib.request.urlopen(raw_link)
taglab_online_version = f_online_version.read().decode('utf-8')

offline_spl_version = taglab_offline_version.split('.')
online_spl_version = taglab_online_version.split('.')

print('offline: ' + str(offline_spl_version))
print('online: ' + str(online_spl_version))

# Check if I need to update TagLab
need_to_update = False
i = 0
while i < len(online_spl_version) and not need_to_update:
    if (not (i < len(offline_spl_version))):
        need_to_update = True
    else:
        if(int(online_spl_version[i]) > int(offline_spl_version[i])):
            need_to_update = True
        elif(int(online_spl_version[i]) < int(offline_spl_version[i])):
            need_to_update = False
            break
    i=i+1


print('Need to update: ' + str(need_to_update))

if need_to_update:
    # File to download
    filename = 'v' + taglab_online_version + '.zip'
    url = base_repo + 'archive/' + filename
    print('Downloading ' + url)
    downloaded_file = tempfile.gettempdir() + '/' +  filename
    try:
        urllib.request.urlretrieve(url, downloaded_file)
    except:
        raise Exception("Cannot download " + url)

    print('Downloaded file is: ' + downloaded_file)

    shutil.copyfile('config.json', 'config.json.bak')

    # Remove directories from TagLab folder
    for filename in os.listdir('.'):
        if filename in to_replace_directories:
            file_path = os.path.join('.', filename)
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    #extract zip
    with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
        zip_ref.extractall('.')

    #move all the content of the extracted zip file in the TagLab folder
    source_dir = './TagLab-' + taglab_online_version
    target_dir = '.'

    file_names = os.listdir(source_dir)

    for file_name in file_names:
        shutil.move(os.path.join(source_dir, file_name), os.path.join(target_dir, file_name))

    shutil.rmtree(source_dir)

    #rebuild coraline
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
