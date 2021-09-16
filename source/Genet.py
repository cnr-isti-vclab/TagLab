from source.Blob import Blob

#convenience class to update genet changes, no need to save anything, genet is stored in the Blobs.
#we store a set of used genets (for creating new ones, and keep track of removed) map genet -> number of blobs
#operations:


#Could be the case to define plugins that attach to properties of the Blobs.
#How it works:
#blob properties -> plugin attach to a specific set of properties.
#must be able to deal when properties are present.

from source.Mask import jointBox;

class Genet:

    def __init__(self, project):
        self.project = project;
        self.updateGenets()
        pass

    # check all blobs and all corrispondences and compute the connected components.
    # will preserve existing genets ids, if possible
    #assign all genets to the first map.
    #propagate all genets to the second map (ensure consistency.


    def updateGenets(self):
        #this array will be used for remapping when enforcing connected components
        genets = []

        #assign remap for blobs with assigned genets
        # for img in self.project.images:
        #     for b in img.annotations.seg_blobs:
        #         if hasattr(b, 'genet') and b.genet is not None:
        #             while len(genets) <= b.genet:
        #                 genets.append(len(genets))
        #             genets[b.genet] = b.genet
        #             print("Image ", img.name, "Blob ", b.id, " has genet ", b.genet)

        #assign genets to blobs with no assigned genet
        count = len(genets)
        for img in self.project.images:
            sorted_blobs = sorted(img.annotations.seg_blobs, key=lambda x: x.id)
            for b in sorted_blobs:
                b.genet = count
                genets.append(count)
                count += 1

        #remap all the correspondending blobs using genets[]
        for corrs in self.project.correspondences.values():
            for index, row in corrs.data.iterrows():
                id1 = int(row['Blob1'])
                id2 = int(row['Blob2'])
                if id1 == -1 or id2 == -1:  #born or dead corals
                    continue
                blob1 = corrs.source.annotations.blobById(id1)
                blob2 = corrs.target.annotations.blobById(id2)

                while blob1.genet != genets[blob1.genet]:
                    blob1.genet = genets[blob1.genet]

                if blob1.genet != blob2.genet:
                    #print("Genet: ", blob2.genet, "mapped to", blob1.genet)

                    g = blob2.genet
                    while True: #if g is remapped also those needs to be remapped
                        destination = genets[g]
                        genets[g] = blob1.genet
                        if destination == g:
                            break
                        g = destination

        for img in self.project.images:
            for b in img.annotations.seg_blobs:
                while b.genet != genets[b.genet]:  #follow the link to the
                    b.genet = genets[b.genet]
                #print("Image ", img.name, "Blob ", b.id, " has genet ", b.genet)


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
        for img in self.project.images:
            fields.append(img.name + " blobs")
            fields.append(img.name + " area")

        lines = {}

        for img in self.project.images:
            for blob in img.annotations.seg_blobs:
                if not blob.genet in lines:
                    lines[blob.genet] = { }

        data = []
        #compact and sort lines.
        count = 0
        for g in sorted(lines.keys()):
            lines[g]['row'] = count
            count += 1
            row = [None] * len(fields)
            row[0] = g
            data.append(row)

        count = 1
        for img in self.project.images:
            for blob in img.annotations.seg_blobs:
                line = lines[blob.genet]
                row = line['row']
                data[row][count] = blob.id
                if not data[row][count+1]:
                    data[row][count+1] = blob.area
                else:
                    data[row][count+1] += blob.area
            count += 2

        import csv

        with open(filename, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(fields)
            for line in data:
                writer.writerow(line)


    def exportSVG(self, filename):
        #remap genets to lines and find bbox per genet.
        lines = {}

        for img in self.project.images:
            for blob in img.annotations.seg_blobs:
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

        for img in self.project.images:
            dx = column*(side + hpadding)

            svg += '<text text-anchor="middle" text-length="' + str(side) + '"  x="' + str(dx + side/2) + '" y="' + str(-150) + '"> ' + \
                '<tspan x="' + str(dx + side/2) + '" font-size="22px" dy="1.2em">' + str(img.name) + "</tspan>" + \
                '<tspan x="' + str(dx + side/2) + '" font-size="18px" dy="1.6em">' + img.acquisition_date + '</tspan></text>'

            for blob in img.annotations.seg_blobs:
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



