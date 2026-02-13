
import numpy as np
import json
import math

from osgeo import gdal, osr
import osgeo.ogr as ogr
import rasterio as rio
from rasterio.plot import reshape_as_raster
from rasterio.mask import mask
from rasterio.control import GroundControlPoint
from rasterio.transform import from_origin, from_gcps
import pandas as pd
from source.Blob import Blob
from source.Shape import Shape
from source.Mask import subtract
from shapely.geometry import Polygon


def mm_to_degrees(mm_pixel_size, center_lat):
    """
    This function converts the length in latitude and longitude degrees.
    One degree of Latitude is always approximately 111.1 km.
    The distance of one degree of Longitude shrinks as you move away from the Equator.
    """

    # Constants
    KM_PER_DEGREE_LAT = 111.1
    KM_PER_DEGREE_LON_EQUATOR = 111.32

    # Convert mm to km
    km_pixel_size = mm_pixel_size / 1000000.0

    # Calculate degrees
    deg_lat = km_pixel_size / KM_PER_DEGREE_LAT

    # Adjust longitude for the curvature of the Earth
    # np.radians is required because cos() takes radians
    deg_lon = km_pixel_size / (KM_PER_DEGREE_LON_EQUATOR * math.cos(math.radians(center_lat)))

    return deg_lon, deg_lat

def georeferencingImageUsingGCPs(img, pixel_size, pix_coords, geo_coords, output_file):
    """
    Assign the georeferencing information to the input image given a set of Ground Control Points.
    """

    # If input_image is (H, W, C), we need to reshape it to (C, H, W) for Rasterio
    width = img.shape[0]
    height = img.shape[1]
    count = img.ndim
    if count == 3 or count == 4:
        img = img.transpose(2, 0, 1)

    # Define GCPs (x=Longitude, y=Latitude)
    gcp1 = GroundControlPoint(row=pix_coords[0], col=pix_coords[1], x=geo_coords[0], y=geo_coords[1])
    gcp2 = GroundControlPoint(row=pix_coords[2], col=pix_coords[3], x=geo_coords[2], y=geo_coords[3])
    transform = from_gcps([gcp1, gcp2])

    # save to a GeoTIFF
    output_path = "memory_to_disk.tif"

    with rio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=count,
        dtype=img.dtype,
        crs=rio.crs.from_epsg(4326), # explicitly setting Lat/Long
        transform=transform,
    ) as dst:
        dst.write(img)


def georeferencingImage(img, pixel_size, anchor_x, anchor_y, anchor_lat, anchor_lon, output_file):
    """
    Given an image without georeferencing information assign georeferencing using WGS EPSG:4326 coordinates.
    """

    # If input_image is (H, W, C), we need to reshape it to (C, H, W) for Rasterio
    width = img.shape[0]
    height = img.shape[1]
    count = img.ndim
    if count == 3 or count == 4:
        img = img.transpose(2, 0, 1)
    pixel_size = img.pixelSize()

    # Calculate the latitude and the longitude of the top-left corner of the image
    lon_res, lat_res = mm_to_degrees(pixel_size, anchor_lat)
    lon_origin = anchor_lon - (anchor_x * lon_res)
    lat_origin = anchor_lat + (anchor_y * lat_res)

    # create the geotransform
    transform = from_origin(lon_origin, lat_origin, lon_res, lat_res)

    # write a GeoTiff
    with rio.open(
            'output_file',
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=count,
            dtype=img.dtype,
            crs='EPSG:4326',
            transform=transform,
    ) as dst:
        dst.write(img)


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


def createPolygonFromWorkingArea(working_area, transform):

    wa_coord = [(working_area[1], working_area[0]), (working_area[1] + working_area[2], working_area[0]), (working_area[1] + working_area[2] , working_area[0] + working_area[3]),(working_area[1], working_area[0]+ working_area[3])]

    # load blob.contour and transform coordinate
    wa_coord_change = changeFormat(wa_coord, transform)
    waPolygon = Polygon(wa_coord_change)

    return waPolygon


def read_attributes(filename):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(filename, 0)
    layer = dataSource.GetLayer(0)
    data = pd.DataFrame()
    for feat in layer:
        shpdict =json.loads(feat.ExportToJson())
        properties = shpdict['properties']
        if data.empty:
            data = pd.DataFrame.from_dict([properties])
        else:
            new_row = pd.DataFrame.from_dict([properties])
            data = pd.concat([data, new_row])
    return data


def read_regions_geometry(filename, georef_filename):

    img = rio.open(georef_filename)
    transform = img.transform

    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(filename, 0)
    layer = dataSource.GetLayer(0)


    #set spatial reference and transformation
    sourceprj = layer.GetSpatialRef()
    targetprj = osr.SpatialReference(wkt = img.crs.wkt)
    #need to check if sourceproj == targetproj
    reproject = osr.CoordinateTransformation(sourceprj, targetprj) #this is a transform

    blobList = []
    for feat in layer:
        transformed = feat.GetGeometryRef()
        transformed.Transform(reproject)

        shpdict = json.loads(feat.ExportToJson())
        if shpdict['geometry']['type'] == 'Polygon':
            blob = Blob(None, 0, 0, 0)
            coord = shpdict['geometry']['coordinates']
            outercontour = coord[0]
            outpointpixels = changeFormatInv([outercontour], transform)
            blob.createFromClosedCurve([np.asarray(outpointpixels)], False)
            for i in range(1, len(coord)):
                innercontourn_i = coord[i]
                innerpointpixels_i = changeFormatInv([innercontourn_i], transform)
                innerblob = Blob(None, 0, 0, 0)
                innerblob.createFromClosedCurve([np.asarray(innerpointpixels_i)], False)
                # FIXME: prevents problem if the innerblob size is less than one pixel, but it is not clear
                #  when it happens
                if innerblob.bbox[2] > 0.9 and innerblob.bbox[3] > 0.9:
                    (mask, box) = subtract(blob.getMask(), blob.bbox, innerblob.getMask(), innerblob.bbox)
                    if mask.any():
                        blob.updateUsingMask(box, mask.astype(int))
            blobList.append(blob)

    return blobList


def read_geometry(filename, georef_filename):

    img = rio.open(georef_filename)
    transform = img.transform

    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(filename, 0)
    layer = dataSource.GetLayer(0)

    shape_list = []
    for feat in layer:
        shpdict = json.loads(feat.ExportToJson())

        if shpdict['geometry']['type'] == 'Polygon':
            coord = shpdict['geometry']['coordinates']
            outercontour = coord[0]
            outpointpixels = changeFormatInv([outercontour], transform)

            inner_contours = []
            for i in range(1, len(coord)):
                innercontourn_i = coord[i]
                innerpointpixels_i = changeFormatInv([innercontourn_i], transform)
                inner_contours.append(np.asarray(innerpointpixels_i))

            shape = Shape(np.asarray(outpointpixels), inner_contours)
            shape_list.append(shape)

        if shpdict['geometry']['type'] == 'Point':
            coord = shpdict['geometry']['coordinates']
            coord_map = changeFormatInv([[coord]], transform)

            sh = Shape(np.asarray(coord_map), None)
            shape_list.append(sh)

    return shape_list



def write_shapefile( project, image, blobs, georef_filename, out_shp):
    """
    https://gis.stackexchange.com/a/52708/8104
    """
    scale_factor = image.pixelSize()
    date = image.acquisition_date
    # load georeference information to use
    img = rio.open(georef_filename)
    geoinfo = img.crs
    transform = img.transform
    annotations = image.annotations

    working_area = project.working_area

    if working_area is not None:
        # only the blobs inside the working area are considered
        blobs = annotations.calculate_inner_blobs(working_area)


    # create the list of visible instances
    name_list = []
    visible_blobs = []
    for blob in blobs:
        if blob.qpath_gitem.isVisible():
            index = blob.blob_name
            name_list.append(index)
            visible_blobs.append(blob)

    # SHAPEFILE NAMES CANNOT BE LONGER THAN 10 characters

    number_of_seg = len(name_list)
    dict = {
        'TL_id': np.zeros(number_of_seg, dtype = np.int64),
        'TL_Date': [],
        'TL_Class': [],
        'TL_Genet': np.zeros(number_of_seg, dtype = np.int64),
        'TL_Cx': np.zeros(number_of_seg),
        'TL_Cy': np.zeros(number_of_seg),
        'TL_Area': np.zeros(number_of_seg),
        'TL_SurfA': np.zeros(number_of_seg),
        'TL_Perim': np.zeros(number_of_seg),
        'TL_Note': []}

    for attribute in project.region_attributes.data:
        key = attribute["name"]
        if attribute['type'] in ['string', 'keyword']:
            dict[key] = []
        elif attribute['type'] in ['integer number', 'boolean']:
            dict[key] = np.zeros(number_of_seg, dtype = np.int64)
        elif attribute['type'] in ['decimal number']:
            dict[key] = np.zeros(number_of_seg, dtype = np.float64)
        else:
            # unknown attribute type, not saved
            pass

    for i, blob in enumerate(visible_blobs):
        dict['TL_id'][i] = blob.id
        dict['TL_Date'].append(date)
        dict['TL_Class'].append(blob.class_name)
        dict['TL_Cx'][i] = round(blob.centroid[0], 1)
        dict['TL_Cy'][i] = round(blob.centroid[1], 1)
        dict['TL_Area'][i] = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
        if blob.surface_area > 0.0:
            dict['TL_SurfA'][i] = round(blob.surface_area * (scale_factor) * (scale_factor) / 100, 2)
        dict['TL_Perim'][i] = round(blob.perimeter * scale_factor / 10, 1)

        if blob.genet is not None:
            dict['TL_Genet'][i] = blob.genet

        dict['TL_Note'].append(blob.note)

        for attribute in project.region_attributes.data:

            key = attribute["name"]

            try:
                value = blob.data[key]
            except:
                value = None

            if attribute['type'] == 'integer number':

                if value is not None:
                    dict[key][i] = value
                else:
                    dict[key][i] = 0

            elif attribute['type'] == 'boolean':

                if value is not None:
                    dict[key][i] = 1 if value else 0
                else:
                    dict[key][i] = 0

            elif attribute['type'] == 'decimal number':

                if value is not None:
                    dict[key][i] = value
                else:
                    dict[key][i] = np.NaN

            else:
                if value is not None:
                    dict[key].append(value)
                else:
                    dict[key].append('')

    # # convert blobs in polygons
    polygons = []
    for blob in visible_blobs:
        if blob.qpath_gitem.isVisible():
            polygon = createPolygon(blob, transform)
            polygons.append(polygon)

    # Now convert them to a shapefile with OGR
    outDriver = ogr.GetDriverByName('Esri Shapefile')
    outDataSource = outDriver.CreateDataSource(out_shp)
    srs = osr.SpatialReference()
    if geoinfo is not None:
        srs.ImportFromWkt(geoinfo.wkt)

    # create a layer
    outLayer = outDataSource.CreateLayer("polygon", srs, geom_type=ogr.wkbPolygon)
    OGRTypes = {int: ogr.OFTInteger, str: ogr.OFTString, float: ogr.OFTReal}
    defn = outLayer.GetLayerDefn()
    # Create attribute fields according to the data types


    for key in list(dict.keys()):

            if type(dict[key]) == list:
                outLayer.CreateField(ogr.FieldDefn(key, OGRTypes[str]))
            elif dict[key].dtype == np.int64 or dict[key].dtype == np.int32:
                outLayer.CreateField(ogr.FieldDefn(key, OGRTypes[int]))
            else:
                outLayer.CreateField(ogr.FieldDefn(key, OGRTypes[float]))

    for i in range(len(polygons)):
        feat = ogr.Feature(defn)
        geom = ogr.CreateGeometryFromWkb(polygons[i].wkb)
        feat.SetGeometry(geom)

        for key in list(dict.keys()):
            if type(dict[key]) == list:
                feat.SetField(key, dict[key][i])

            elif dict[key].dtype == np.int64 or dict[key].dtype == np.int32:
                feat.SetField(key, int(dict[key][i]))

            else:
                feat.SetField(key, float(dict[key][i]))

        # Make a geometry, from Shapely object
        outLayer.CreateFeature(feat)
        feat = geom = None  # destroy these

    # Save and close everything
    ds = layer = feat = geom = None

def load_georef(image):
    # load georeference information to use
    img = rio.open(image)
    geoinfo = img.crs
    transform = img.transform
    return geoinfo, transform

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

def saveGeorefLabelMap(label_map, georef_filename, working_area, out_name):

    ## TO DO: CLEAN UP THIS FUNCTION!

    # create a georeferenced label image (as raster)
    img = rio.open(georef_filename)
    meta = img.meta
    transform = img.transform
    crs = img.crs

    myLabel = reshape_as_raster(label_map)
    myLabel_meta = meta.copy()
    myLabel_meta.update({"dtype": rio.uint8,
                         "count": 3,
                         "nodata": None})
    with rio.open(out_name + ".tif", "w", **myLabel_meta) as dest:
        dest.write(myLabel)

    if working_area is not None:

        dataset = rio.open(out_name + ".tif")
        # convert the working area into a polygon
        working_area_polygon = createPolygonFromWorkingArea(working_area, transform)
        # crop the raster using the working area polygon
        out_image, out_transform = rio.mask.mask(dataset, [working_area_polygon], crop=True)
        out_meta = dataset.meta.copy()
        out_meta.update({"driver": "GTiff",
                          "height": out_image.shape[1],
                          "width": out_image.shape[2],
                          "transform": out_transform})
        dataset.close()

        with rio.open(out_name + ".tif", "w", **out_meta) as dest:
            dest.write(out_image)


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
