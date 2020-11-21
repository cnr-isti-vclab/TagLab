
import numpy as np
from shapely.geometry import Polygon
from osgeo import gdal, osr
import osgeo.ogr as ogr
import rasterio as rio
from rasterio.plot import reshape_as_raster
from rasterio.mask import mask


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

def write_shapefile(blobs, georef_filename, out_shp):
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
            colors.append('#%02X%02X%02X' % tuple(blob.class_color))
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

    # filter out null values and jumps
    slope[slope > 87] = 0

    for blob in blobs:
        non_null = blob.getMask()
        top = blob.bbox[0]
        left = blob.bbox[1]
        right = left + blob.bbox[2]
        bottom = top + blob.bbox[3]
        slope_crop = slope[top:bottom, left:right]
        surface_area = (non_null / abs(np.cos(np.radians(slope_crop)))).sum()
        # surface_area = ((area_px*non_null/(abs(np.cos(np.radians(slope_crop))))).sum())/10**2
        blob.area = surface_area

         # volume = (array * (area_px*non_null)).sum()*10**6

