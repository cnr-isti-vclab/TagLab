from source.tools.Tool import Tool

class Assign(Tool):
    def __init__(self, viewerplus):
        super(Assign, self).__init__(viewerplus)
        self.active_label = None


    def setActiveLabel(self, label):

        self.active_label = label


    def leftPressed(self, x, y, mods):

        if self.active_label is None:
            return #do nothing, no label is set

        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)
        if selected_blob is None:
            return

        self.viewerplus.addToSelectedList(selected_blob)

        genets = set()
        for blob in self.viewerplus.selected_blobs:
            if blob.genet is not None \
                    and blob.genet >= 0:
                genets.add(blob.genet)
            else:
                self.viewerplus.setBlobClass(blob, self.active_label)

        project = self.viewerplus.project
        for image in project.images:
            blobs = [blob for blob in image.annotations.seg_blobs if blob.genet in genets]
            for blob in blobs:
                self.viewerplus.setBlobClass(blob, self.active_label)

#            if image == self.viewerplus2.image //we need to update also the other viewer!!!!
#            2) l'undo ha lo stesso problema, posso aggiungere i blob ma devono essere fatti per ogni immagine.



        message ="[TOOL][ASSIGN] Blob(s) assigned ({:d}) (CLASS={:s}).".format(len(self.viewerplus.selected_blobs), self.active_label)
        self.viewerplus.logfile.info(message)

        self.viewerplus.saveUndo()
        self.viewerplus.resetSelection()