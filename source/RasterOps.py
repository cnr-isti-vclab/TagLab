
import ogr
import rasterio as rio
import numpy as np
from shapely.geometry import Polygon
from osgeo import gdal,osr
from rasterio.plot import reshape_as_raster



def changeFormat(contour,georef):

    """
    convert blob coordinates for Polygon shapefiles. Coord are in pixels while pointsgeo are in mm
    """
    coords=[]
    pointsgeo = []
    for coord in contour:
        coord = tuple(coord)
        coords.append(coord)

    if georef is not None:

        for points in coords:
            x = points[0]
            y = points[1]
            pointgeo = georef.transform * (x, y)
            pointsgeo.append(pointgeo)

        return pointsgeo

    else:
        return coords


def createPolygon(blob,georef):

    # load blob.contour and transform coordinate
    exterior =  changeFormat(blob.contour,georef)
    exteriorPolygon = Polygon(exterior)

    inners=[]
    for inner in blob.inner_contours:
            interior=changeFormat(inner,georef)
            innerPolygon=Polygon(interior)
            inners.append(innerPolygon)
    newPolygon= Polygon(exteriorPolygon.exterior.coords, [inner.exterior.coords for inner in inners])

    return newPolygon



def write_shapefile(polygons, myIds, georef, out_shp):
    """
    https://gis.stackexchange.com/a/52708/8104
    """

    # Now convert it to a shapefile with OGR
    outDriver = ogr.GetDriverByName('Esri Shapefile')
    outDataSource = outDriver.CreateDataSource(out_shp)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(georef.crs.wkt)
    outLayer = outDataSource.CreateLayer("polygon", srs, geom_type=ogr.wkbPolygon)

    # Add id to polygon
    outLayer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    defn = outLayer.GetLayerDefn()

    ## If there are multiple geometries, put the "for" loop here


    for i in range(len(myIds)):

        # Create a new feature (attribute and geometry)
        feat = ogr.Feature(defn)
        feat.SetField('id', myIds[i])

        # Make a geometry, from Shapely object
        geom = ogr.CreateGeometryFromWkb(polygons[i].wkb)
        feat.SetGeometry(geom)

        outLayer.CreateFeature(feat)
        feat = geom = None  # destroy these

    # Save and close everything
    ds = layer = feat = geom = None





def saveClippedTiff(polygons,georef,name):

    out_image, out_transform = rio.mask.mask(georef, polygons, crop=True)
    # num_non_null = (out_image != 500000).sum()
    out_meta = georef.meta
    # area= out_meta['transform'][0] ** 2*out_image
    out_meta.update({"driver": "GTiff",
                      "height": out_image.shape[1],
                      "width": out_image.shape[2],
                      "transform": out_transform})

    with rio.open(name, "w", **out_meta) as dest:
        dest.write(out_image)



def saveGeorefLabelMap(label_map, src, out_name):

    # myLabel = io.imread('D:\\MOOREA\\DEM\\Plot_18_2018\\Plot_18_2018_RGB.png')
    myLabel = reshape_as_raster(label_map)
    myLabel_meta = src.meta.copy()

    myLabel_meta.update({"dtype": rio.uint8,
                         "count": 3,
                         "nodata": None})

    with rio.open(out_name + ".tif", "w", **myLabel_meta) as dest:
        dest.write(myLabel)



def exportSlope(raster, filename):
    # save slope raster
    gdal.DEMProcessing(filename+'.tif', raster, 'slope')
    with rio.open(filename+'.tif') as dataset:
         slope = dataset.read(1)
    return slope


def adjustAreaUsingSlope(polygon, areaor, georef):

    array = georef.read()
    slope= exportSlope("D:\\MOOREA\\DEM\\Plot_18_2018\\2018-Plot18_2m_PL51_DEM_0.6666mm-32b.tif", 'slope')
    meta = georef.meta
    area_px = meta['transform'][0] ** 2
    non_null = (array != array.min()).astype(int)
    area = (area_px*non_null).sum()*10**4

    # filter out null values and jumps
    # slope[slope < 9998] = 0
    slope[slope > 87] = 0
    surface_area = (area_px*non_null/(abs(np.cos(np.radians(slope))))).sum()*10**4
    # volume = (array * (area_px*non_null)).sum()*10**6
