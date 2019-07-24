import os

class Configuration:

    def __init__(self):

        ##### DATA INITIALIZATION #####

        # PROJECT FOLDERS
        # self.projectname = "RGB"
        self.image_map_filename = "C:\\TOOL\\map\\CROP.jpg"
        self.project_dir = "C:\\TOOL\\projects"

        # al momento in projects non mette nulla tranne la thumbnail

        # MAP INFO
        self.map_filename = os.path.join(self.project_dir, "CROP.jpg")
        self.MAP_WIDTH = 0
        self.MAP_HEIGHT = 0

        # EXPORT
        self.export_dir = os.path.join(self.project_dir, "export")

    def createProjectFolder(self):

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

