
import numpy as np
import ast
from shapely.geometry import Polygon
from osgeo import gdal, osr
import osgeo.ogr as ogr
import rasterio as rio
from rasterio.plot import reshape_as_raster
from rasterio.mask import mask
import pandas as pd
from source.Blob import Blob
from source.Mask import subtract
from numpy.linalg import inv


def changeFormat(contour, transform):
    """
    convert blob coordinates for Polygon shapefiles. Coord are in pixels while pointsgeo are in mm
    """
    coords = []
    pointsgeo = []
    for coord in contour:
        coord = tuple(coord)
        coords.append(coord)

    if transform is not None:
        for points in coords:
            x = points[0]
            y = points[1]
            pointgeo = transform * (x, y)
            pointsgeo.append(pointgeo)
        return pointsgeo
    else:
        return coords


def changeFormatInv(coord, transform):
    """
    convert polygon coordinate in pixel coordinates
    # """
    # transformr = np.reshape(transform, (3, 3))
    # transformInv = inv(transformr)
    pointpixels = []
    #va controllato se esiste
    if transform is not None:
        for points in coord[0]:
            xref = points[0]
            yref = points[1]
            pointpix = ~transform * (xref, yref)
            pointpixels.append(pointpix)
        return pointpixels

def changeFormatInvPoint(coord, transform):
    """
    convert poligon coordinate in pixel coordinates
    # """
    if transform is not None:
        xref = coord[0]
        yref = coord[1]
        pointpix = ~transform * (xref, yref)
        return pointpix


def createPolygon(blob, transform):

    # load blob.contour and transform coordinate
    exterior = changeFormat(blob.contour, transform)
    exteriorPolygon = Polygon(exterior)

    inners=[]
    for inner in blob.inner_contours:
            interior=changeFormat(inner, transform)
            innerPolygon = Polygon(interior)
            inners.append(innerPolygon)
    newPolygon = Polygon(exteriorPolygon.exterior.coords, [inner.exterior.coords for inner in inners])

    return newPolygon


def read_attributes(filename):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(filename, 0)
    layer = dataSource.GetLayer(0)
    Data = pd.DataFrame()
    for feat in layer:
        shpdict =json.loads(feat.ExportToJson())
        properties = shpdict['properties']
        if Data.empty:
            Data = pd.DataFrame.from_dict([properties])
        else:
            data = pd.DataFrame.from_dict([properties])
            Data = Data.append(data, ignore_index=True)
    return Data

def read_geometry(filename, georef_filename, shapetype):

    img = rio.open(georef_filename)
    transform = img.transform

    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(filename, 0)
    layer = dataSource.GetLayer(0)

    if shapetype == 'Label':
        blobList = []
        for feat in layer:
            shpdict =json.loads(feat.ExportToJson())
            if shpdict['geometry']['type'] == 'Polygon':
               blob = Blob(None, 0, 0, '0')
               coord = shpdict['geometry']['coordinates']
               outercontourn = coord[0]
               outpointpixels = changeFormatInv([outercontourn], transform)
               blob.createFromClosedCurve([np.asarray(outpointpixels)])
               for i in range(1, len(coord)):
                   innercontourn_i = coord[i]
                   innerpointpixels_i = changeFormatInv([innercontourn_i], transform)
                   innerblob = Blob(None, 0, 0, '0')
                   innerblob.createFromClosedCurve([np.asarray(innerpointpixels_i)])
                   (mask, box) = subtract(blob.getMask(), blob.bbox, innerblob.getMask(), innerblob.bbox)
                   if mask.any():
                       blob.updateUsingMask(box, mask.astype(int))
               blobList.append(blob)

    if shapetype == 'Sampling':

        # sampling puo'avere cerchi bucati? Contorni interni? che forme ammettiamo?
        centers =[]
        rays = []
        for feat in layer:
            shpdict = json.loads(feat.ExportToJson())
            if shpdict['geometry']['type'] == 'Polygon':
                blob = Blob(None, 0, 0, '0')
                coord = shpdict['geometry']['coordinates']
                outercontourn = coord[0]
                outpointpixels = changeFormatInv([outercontourn], transform)
                blob.createFromClosedCurve([np.asarray(outpointpixels)])
                c = round((4*np.pi*blob.area)/ np.square(blob.perimeter), 2)

                center = blob.centroid
                r = (blob.perimeter)/(2*np.pi)


                print(c)






    return blobList





    # layerDefinition = layer.GetLayerDefn()
    #
    # GET FIELDS of layer's features
    # fields = []
    # for i in range(layerDefinition.GetFieldCount()):
    #     fieldName = layerDefinition.GetFieldDefn(i).GetName()
    #     fieldTypeCode = layerDefinition.GetFieldDefn(i).GetType()
    #     fieldType = layerDefinition.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
    #     fieldWidth = layerDefinition.GetFieldDefn(i).GetWidth()
    #     fieldPrecision = layerDefinition.GetFieldDefn(i).GetPrecision()
    #     field = [fieldName, fieldType]
    #     fields.append(field)

    # #GET FEATURES
    # num_features = layer.GetFeatureCount()
    # pt = np.zeros((num_features, ), dtype=object)
    # values = np.zeros((num_features, len(fields)), dtype=object)
    # for i in range(0, num_features):
    #     for j in range(0, len(fields)):
    #         if fields[j][2] == str:
    #             value_name = layer[i].GetFieldAsString(fields[j][0])
    #         else:
    #             value_name = layer[i].GetField(fields[j][0])
    #         values[i][j] = value_name


    # blobList = []
    # Data = pd.DataFrame()
    #
    #
    # for feat in layer:
    #     # shpdict= ast.literal_eval(feat.ExportToJson())
    #     shpdict =json.loads(feat.ExportToJson())
    #     if shpdict['geometry']['type'] == 'Polygon':
    #        blob = Blob(None, 0, 0, '0')
    #        coord = shpdict['geometry']['coordinates']
    #        outercontourn = coord[0]
    #        outpointpixels = changeFormatInv([outercontourn], transform)
    #        blob.createFromClosedCurve([np.asarray(outpointpixels)])
    #        for i in range(1, len(coord)):
    #            innercontourn_i = coord[i]
    #            innerpointpixels_i = changeFormatInv([innercontourn_i], transform)
    #            innerblob = Blob(None, 0, 0, '0')
    #            innerblob.createFromClosedCurve([np.asarray(innerpointpixels_i)])
    #            (mask, box) = subtract(blob.getMask(), blob.bbox, innerblob.getMask(), innerblob.bbox)
    #            if mask.any():
    #                blob.updateUsingMask(box, mask.astype(int))
    #        blobList.append(blob)

    #        # The attribute field can be empty
    #        properties = shpdict['properties']
    #        if Data.empty:
    #         Data = pd.DataFrame.from_dict([properties])
    #        else:
    #         data = pd.DataFrame.from_dict([properties])
    #         Data = Data.append(data, ignore_index=True)
    #
    #     elif shpdict['geometry']['type'] == 'Point':
    #          coord = shpdict['geometry']['coordinates']
    #          #not integers
    #          coord_= changeFormatInvPoint(coord, transform)
    #
    #          properties = shpdict['properties']
    #          if Data.empty:
    #              Data = pd.DataFrame.from_dict([properties])
    #          else:
    #              data = pd.DataFrame.from_dict([properties])
    #              Data = Data.append(data, ignore_index=True)
    #
    #
    # return blobList, Data



def write_shapefile(project, blobs, georef_filename, out_shp):
    """
    https://gis.stackexchange.com/a/52708/8104
    """
    # load georeference information to use
    img = rio.open(georef_filename)
    geoinfo = img.crs
    transform = img.transform

    # convert blobs in polygons
    polygons = []
    ids = []
    classnames = []
    colors = []

    for blob in blobs:
        if blob.qpath_gitem.isVisible():
            polygon = createPolygon(blob, transform)
            ids.append(blob.id)
            classnames.append(blob.class_name)
            class_color = project.classColor(blob.class_name)
            colors.append('#%02X%02X%02X' % tuple(class_color))
            polygons.append(polygon)

    # Now convert them to a shapefile with OGR
    outDriver = ogr.GetDriverByName('Esri Shapefile')
    outDataSource = outDriver.CreateDataSource(out_shp)
    srs = osr.SpatialReference()
    if geoinfo is not None:
        srs.ImportFromWkt(geoinfo.wkt)
    outLayer = outDataSource.CreateLayer("polygon", srs, geom_type=ogr.wkbPolygon)

    # Add id to polygon
    outLayer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('class', ogr.OFTString))
    defn = outLayer.GetLayerDefn()

    ## If there are multiple geometries, put the "for" loop here
    for i in range(len(ids)):
        # Create a new feature (attribute and geometry)
        feat = ogr.Feature(defn)
        feat.SetField('id', ids[i])
        feat.SetField('class', classnames[i])

        # Make a geometry, from Shapely object
        geom = ogr.CreateGeometryFromWkb(polygons[i].wkb)
        feat.SetGeometry(geom)
        feat.SetStyleString('BRUSH(fc:' + colors[i] + ')')
        outLayer.CreateFeature(feat)
        feat = geom = None  # destroy these

    # Save and close everything
    ds = layer = feat = geom = None


def saveClippedTiff(input, blobs, georef_filename, name):

    # load georeference information to use
    img = rio.open(georef_filename)
    geoinfo = img.crs
    transform = img.transform

    # convert blobs into polygons
    mypolygons = []
    for blob in blobs:
        if blob.qpath_gitem.isVisible():
            polygon = createPolygon(blob, transform)
            mypolygons.append(polygon)

    dataset = rio.open(input)
    out_image, out_transform = rio.mask.mask(dataset, mypolygons, crop=True)
    # num_non_null = (out_image != 500000).sum()
    out_meta = dataset.meta
    # area= out_meta['transform'][0] ** 2*out_image
    out_meta.update({"driver": "GTiff",
                      "height": out_image.shape[1],
                      "width": out_image.shape[2],
                      "transform": out_transform})

    with rio.open(name, "w", **out_meta) as dest:
        dest.write(out_image)

def saveGeorefLabelMap(label_map, georef_filename, out_name):

    # load georeference information to use
    img = rio.open(georef_filename)
    meta = img.meta

    myLabel = reshape_as_raster(label_map)
    myLabel_meta = meta.copy()

    myLabel_meta.update({"dtype": rio.uint8,
                         "count": 3,
                         "nodata": None})

    with rio.open(out_name + ".tif", "w", **myLabel_meta) as dest:
        dest.write(myLabel)

def exportSlope(raster, filename):

    # process slope raster and save it
    # IMPORTANT NOTE: DEMprocessing using the INTERNAL scale of the GeoTiff, so the
    # geo transform MUST BE CORRECT to obtain a reliable calculation of the slope !!
    gdal.DEMProcessing(filename, raster, 'slope')
    with rio.open(filename) as dataset:
         slope = dataset.read(1).astype(np.float32)
    return slope

def calculateAreaUsingSlope(depth_filename, blobs):
    """'Outputs areas as number of pixels"""

    slope = exportSlope(depth_filename, 'slope.tif')
    height= slope.shape[0]
    width = slope.shape[1]

    # filter out null values and jumps
    slope[slope > 87] = 0

    for blob in blobs:
        blob_copy= blob.copy()
        if blob_copy.bbox[0] < 0:
           blob_copy.bbox[3] = blob_copy.bbox[0] + blob_copy.bbox[3]
           blob_copy.bbox[0] = 0

        if blob_copy.bbox[1] < 0:
            blob_copy.bbox[2] = blob_copy.bbox[0] + blob_copy.bbox[2]
            blob_copy.bbox[1] = 0

        if blob_copy.bbox[1] + blob_copy.bbox[2] > width - 1:
           blob_copy.bbox[2] = width - 1 - blob_copy.bbox[1]

        if blob_copy.bbox[0] + blob_copy.bbox[3] > height-1:
            blob_copy.bbox[3] = height - 1 - blob_copy.bbox[0]

        non_null = blob_copy.getMask()
        top = blob_copy.bbox[0]
        left = blob_copy.bbox[1]
        right = left + blob_copy.bbox[2]
        bottom = top + blob_copy.bbox[3]

        slope_crop = slope[top:bottom, left:right]
        surface_area = (non_null / abs(np.cos(np.radians(slope_crop)))).sum()
        blob.surface_area = surface_area
