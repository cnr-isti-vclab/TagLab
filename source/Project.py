class Project(object):
    def __init__(self):
        self.name = None            #label of the project (not the filename)
        self.filename = None        #filename of the project json
        self.path = None            #path to the project json

        self.labels = {}            #list of labels used in this project
        self.images = []            #list of annotated images
        self.correspondences = []   #list of correspondences betweeen labels in images
                                    #[ [source_img: , target_img:, [[23, 12, [grow, shrink, split, join] ... ] }
        self.spatial_reference_system = None   #if None we assume coordinates in pixels (but Y is up or down?!)
        self.metadata = {}  # project metadata => keyword -> value
        self.image_metadata_template = {}  # description of metadata keywords expected in images
                                           # name: { type: (integer, date, string), mandatory: (true|false), default: ... }

