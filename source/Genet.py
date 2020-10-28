from source.Project import Project
from source.Blob import Blob

#convenience class to update genet changes, no need to save anything, genet is stored in the Blobs.
#we store a set of used genets (for creating new ones, and keep track of removed) map genet -> number of blobs
#operations:


#Could be the case to define plugins that attach to properties of the Blobs.
#How it works:
#blob properties -> plugin attach to a specific set of properties.
#must be able to deal when properties are present.


class Genet:

    def __init__(self, images, correspondences) {

    }

    # update blob with a new genet first empty genet (starting from 1)
    def addBlob(self, blob):
        return 1
    #a blob was removed update genet
    def removeBlob(self, image_id, blob):
        #if not genet, retunr
        #if genet count = 1 free genet
        #look for correspondences, we might need to split a graph in 2 or more.
        pass

    def updateBlobs(self, blobs):
        #check connectivity for all the blobs and update the genets.
        pass

    def save(self):
        return {}



