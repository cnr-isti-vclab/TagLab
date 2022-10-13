from source.Blob import Blob

#convenience class to update genet changes, no need to save anything, genet is stored in the Blobs.
#we store a set of used genets (for creating new ones, and keep track of removed) map genet -> number of blobs
#operations:

#Could be the case to define plugins that attach to properties of the Blobs.
#How it works:
#blob properties -> plugin attach to a specific set of properties.
#must be able to deal when properties are present.

from source.Mask import jointBox
from source.Annotation import Annotation

class Genet:

    def __init__(self, project):
        self.project = project;
        self.updateGenets()
        pass

    # check all blobs and all corrispondences and compute the connected components.
    # will preserve existing genets ids, if possible
    #assign all genets to the first map.
    #propagate all genets to the second map (ensure consistency.


    #union find algorithm to find connected components
    def updateGenets(self):
        parents = []

        count = len(parents)
        for img in self.project.images:
            sorted_blobs = sorted(img.annotations.seg_blobs, key=lambda x: x.id)
            for blob in sorted_blobs:
                blob.genet = count
                parents.append(count)
                count += 1

        def root(p): 
            while p != parents[p]:
                p = parents[p]
            return p

        def link(p0, p1):
            r0 = root(p0)
            r1 = root(p1)
            parents[r1] = r0

        for corrs in self.project.correspondences.values():
            for index, row in corrs.data.iterrows():
                id1 = int(row['Blob1'])
                id2 = int(row['Blob2'])
                if id1 == -1 or id2 == -1:  #born or dead corals
                    continue
                blob1 = corrs.source.annotations.blobById(id1)
                blob2 = corrs.target.annotations.blobById(id2)


                if blob1.genet != blob2.genet:
                    link(blob1.genet, blob2.genet)

        remap = [None]*len(parents) #keep tracks of where each root points to.
        count = 0
        for i in range(len(parents)):
            r = root(i)
            if remap[r] is None:
                remap[r] = count
                count += 1
            remap[i] = remap[r]

        for img in self.project.images:
            for blob in img.annotations.seg_blobs:
                blob.genet = remap[blob.genet]

         #update corrs genets.
        for corrs in self.project.correspondences.values():            
            for index, row in corrs.data.iterrows():
                id1 = int(row['Blob1'])
                id2 = int(row['Blob2'])
                
                if id1 != -1:
                    blob1 = corrs.source.annotations.blobById(id1)
                    corrs.data.loc[index, 'Genet'] = blob1.genet
                else:
                    blob2 = corrs.target.annotations.blobById(id2)
                    corrs.data.loc[index, 'Genet'] = blob2.genet



    #ox and oy are the origin of bbox of the blob, dx and dy is a translation in svg.
    def path(self, contour, ox, oy, scale, dx, dy):
        path = ""
        first = True
        for i in range(contour.shape[0]):
            if first:
                path += " M "
                first = False
            else:
                path += " L "

            x = (contour[i, 0] - ox) * scale + dx
            y = (contour[i, 1] - oy) * scale + dy
            path += str(round(x, 1)) + " " + str(round(y, 1))
        return path

    def exportCSV(self, filename):
        fields = ['genet']

        working_area = self.project.working_area
        self.blobs =[]

        for img in self.project.images:
            # writing both classes seems redundant in matching, but it's not for born and dead
            fields.append(img.name + " Class name")
            fields.append(img.name + " Object id")
            fields.append(img.name + " Area")
        lines = {}

        for img in self.project.images:
            if working_area is None:
                blobs = img.annotations.seg_blobs
            else:
                blobs = img.annotations.calculate_inner_blobs(working_area)

            self.blobs.append(blobs)

            for blob in blobs:
                if not blob.genet in lines:
                    lines[blob.genet] = { }
        data = []
        #compact and sort lines.
        count = 0
        for g in sorted(lines.keys()):
            lines[g]['row'] = count
            count += 1
            row = [""] * len(fields)
            row[0] = g
            data.append(row)

        count = 1
        for i,img in enumerate(self.project.images):
            scale_factor = img.pixelSize()
            for blob in self.blobs[i]:
                line = lines[blob.genet]
                row = line['row']
                area = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
                data[row][count] += blob.class_name + "  "
                data[row][count+1] += str(blob.id) + "  "
                data[row][count+2] += str(area) + "  "

            count += 3

        import csv

        with open(filename, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(fields)
            for line in data:
                writer.writerow(line)


    def exportSVG(self, filename):
        #remap genets to lines and find bbox per genet.
        lines = {}
        working_area = self.project.working_area
        self.blobs = []

        for img in self.project.images:
            if working_area is None:
                blobs = img.annotations.seg_blobs
            else:
                blobs = img.annotations.calculate_inner_blobs(working_area)

            self.blobs.append(blobs)

            for blob in blobs:
                if not blob.genet in lines:
                    lines[blob.genet] = { 'box': blob.bbox }
                else:
                    lines[blob.genet]['box'] = jointBox([lines[blob.genet]['box'], blob.bbox])

        #compact and sort lines.
        count = 0
        for g in sorted(lines.keys()):
            lines[g]['row'] = count
            count += 1

        svg = "<svg>"
        column = 0
        y = 0
        vpadding = hpadding = 30
        side = 200

        for g in range(0, count):
            svg += '<text font-size="20px" x="' + str(-150) + '" y="' + str(g*(side + vpadding) + 80) + '">genet: ' + str(g) + '</text>'

        for i, img in enumerate(self.project.images):
            dx = column*(side + hpadding)

            svg += '<text text-anchor="middle" text-length="' + str(side) + '"  x="' + str(dx + side/2) + '" y="' + str(-150) + '"> ' + \
                '<tspan x="' + str(dx + side/2) + '" font-size="22px" dy="1.2em">' + str(img.name) + "</tspan>" + \
                '<tspan x="' + str(dx + side/2) + '" font-size="18px" dy="1.6em">' + img.acquisition_date + '</tspan></text>'

            for blob in self.blobs[i]:
                line = lines[blob.genet]
                box = line['box']
                row = line['row']
                scale = side / max(box[2], box[3])
                dy =    row*(side + vpadding)

                brush = self.project.classBrushFromName(blob)

                svg += '<path fill="' + brush.color().name() + '" data-image="' + img.name + '" data-id="' + str(blob.id) + '" d="'
                svg += self.path(blob.contour, box[1], box[0], scale, dx, dy)

                for inner in blob.inner_contours:
                    svg += self.path(inner, box[1], box[0], scale, dx, dy)

                svg += '"></path>\n'
                b = blob.bbox
                cx = (b[1] + b[2]/2 - box[1])*scale + dx - 4
                cy = (b[0] + b[3]/2 - box[0])*scale + dy + 6
                svg += '<text font-size="11px" x="' + str(cx) + '" y="' + str(cy) + '">' + str(blob.id) + '</text>'

            column += 1
        svg += "</svg>"
        f = open(filename, "w")
        f.write(svg)
        f.close()


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



