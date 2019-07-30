# TagLab                                               
# A semi-automatic segmentation tool                                    
#
# Copyright(C) 2019                                         
# Visual Computing Lab                                           
# ISTI - Italian National Research Council                              
# All rights reserved.                                                      
                                                                          
# This program is free software; you can redistribute it and/or modify      
# it under the terms of the GNU General Public License as published by      
# the Free Software Foundation; either version 2 of the License, or         
# (at your option) any later version.                                       
                                                                           
# This program is distributed in the hope that it will be useful,           
# but WITHOUT ANY WARRANTY; without even the implied warranty of            
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)          
# for more details.                                               

import os

class Configuration:

    def __init__(self):

        ##### DATA INITIALIZATION #####

        # CHOOSE YOUR MAP
        self.image_map_filename = "./map/CROP.jpg"
        # CHOOSE A PROJECT DIR
        self.project_dir = "./projects"
        # CHOOSE A EXPORT DIR
        self.export_dir = "./exports"


        # MAP INFO - OPTIONAL: CHANGE THE THUMBNAIL NAME ACCORDING TO YOUR MAP NAME
        self.map_filename = os.path.join(self.project_dir, "CROP.png")
        self.MAP_WIDTH = 0
        self.MAP_HEIGHT = 0

        # EXPORT
        # self.export_dir = os.path.join(self.export_dir, "exports")

    def createProjectFolder(self):

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

    def createExportFolder(self):

        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

