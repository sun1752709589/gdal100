from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import numpy as np
import pdb

def getSRSPair(dataset):
    '''
    获得给定数据的投影参考系和地理参考系
    :param dataset: GDAL地理数据
    :return: 投影参考系和地理参考系
    '''
    prosrs = osr.SpatialReference()
    prosrs.ImportFromWkt(dataset.GetProjection())
    geosrs = prosrs.CloneGeogCS()
    return prosrs, geosrs

def geo2lonlat(dataset, x, y):
    '''
    将投影坐标转为经纬度坐标（具体的投影坐标系由给定数据确定）
    :param dataset: GDAL地理数据
    :param x: 投影坐标x
    :param y: 投影坐标y
    :return: 投影坐标(x, y)对应的经纬度坐标(lon, lat)
    '''
    prosrs, geosrs = getSRSPair(dataset)
    ct = osr.CoordinateTransformation(prosrs, geosrs)
    coords = ct.TransformPoint(x, y)
    return coords[:2]


def lonlat2geo(dataset, lon, lat):
    '''
    将经纬度坐标转为投影坐标（具体的投影坐标系由给定数据确定）
    :param dataset: GDAL地理数据
    :param lon: 地理坐标lon经度
    :param lat: 地理坐标lat纬度
    :return: 经纬度坐标(lon, lat)对应的投影坐标
    '''
    prosrs, geosrs = getSRSPair(dataset)
    ct = osr.CoordinateTransformation(geosrs, prosrs)
    coords = ct.TransformPoint(lon, lat)
    return coords[:2]

def imagexy2geo(dataset, row, col):
    '''
    根据GDAL的六参数模型将影像图上坐标（行列号）转为投影坐标或地理坐标（根据具体数据的坐标系统转换）
    :param dataset: GDAL地理数据
    :param row: 像素的行号
    :param col: 像素的列号
    :return: 行列号(row, col)对应的投影坐标或地理坐标(x, y)
    '''
    trans = dataset.GetGeoTransform()
    px = trans[0] + col * trans[1] + row * trans[2]
    py = trans[3] + col * trans[4] + row * trans[5]
    return px, py

def geo2imagexy(dataset, x, y):
    '''
    根据GDAL的六 参数模型将给定的投影或地理坐标转为影像图上坐标（行列号）
    :param dataset: GDAL地理数据
    :param x: 投影或地理坐标x
    :param y: 投影或地理坐标y
    :return: 影坐标或地理坐标(x, y)对应的影像图上行列号(row, col)
    '''
    trans = dataset.GetGeoTransform()
    a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
    b = np.array([x - trans[0], y - trans[3]])
    return np.linalg.solve(a, b)  # 使用numpy的linalg.solve进行二元一次方程的求解

def imagexy2lonlat(dataset,row, col):
    '''
    影像行列转经纬度：
    ：通过影像行列转平面坐标
    ：平面坐标转经纬度
    '''
    coords = imagexy2geo(dataset, row, col)
    coords2 = geo2lonlat(dataset,coords[0], coords[1])
    return (coords2[0], coords2[1])

def lonlat2imagexy(dataset,x, y):
    '''
    影像行列转经纬度：
    ：通过经纬度转平面坐标
    ：平面坐标转影像行列
    '''
    coords = lonlat2geo(dataset, x, y)
    coords2 = geo2imagexy(dataset,coords[0], coords[1])
    return (int(round(abs(coords2[0]))), int(round(abs(coords2[1]))))

def get_tiff_polygon(dataset):
    trans = dataset.GetGeoTransform()
    xpxs = dataset.RasterXSize
    ypxs = dataset.RasterYSize
    return get_polygon(dataset, trans[0], trans[3], xpxs, ypxs)

def get_polygon(dataset, origin_x, origin_y, offset_x, offset_y):
    new_x, new_y = imagexy2geo(dataset, offset_x, offset_y)
    polygon = 'POLYGON (('
    polygon += (str(origin_x) + ' ' + str(origin_y))
    polygon += (',' + str(new_x) + ' ' + str(origin_y))
    polygon += (',' + str(new_x) + ' ' + str(new_y))
    polygon += (',' + str(origin_x) + ' ' + str(new_y))
    polygon += (',' + str(origin_x) + ' ' + str(origin_y))
    polygon += '))'
    return polygon

# intersection.ExportToWkt()

def tileclip(file_path, out_path, block_xsize, block_ysize, polygon):
    # 读取要切的原图
    in_ds = gdal.Open(file_path)
    # 波段数
    nb = in_ds.RasterCount
    # 读取原图中的每个波段
    bands_list = []
    for i in range(1, nb + 1, 1):
        bands_list.append(in_ds.GetRasterBand(i))
    # 原始图大小
    xpxs = in_ds.RasterXSize
    ypxs = in_ds.RasterYSize
    # 裁剪行列
    xcount = xpxs // block_xsize if xpxs % block_xsize == 0 else (xpxs // block_xsize) + 1
    ycount = ypxs // block_ysize if ypxs % block_ysize == 0 else (ypxs // block_ysize) + 1
    pdb.set_trace()
    for y in range(ycount):
        for x in range(xcount):
            offset_x = x * block_xsize
            offset_y = y * block_ysize
            if (offset_x + block_xsize) > xpxs:
                block_xsize_tmp = xpxs - offset_x
            else:
                block_xsize_tmp = block_xsize
            if (offset_y + block_ysize) > ypxs:
                block_ysize_tmp = ypxs - offset_y
            else:
                block_ysize_tmp = block_ysize
            # 读取原图仿射变换参数值
            ori_transform = in_ds.GetGeoTransform()
            top_left_x = ori_transform[0]  # 左上角x坐标
            w_e_pixel_resolution = ori_transform[1] # 东西方向像素分辨率
            top_left_y = ori_transform[3] # 左上角y坐标
            n_s_pixel_resolution = ori_transform[5] # 南北方向像素分辨率
            # 根据反射变换参数计算新图的原点坐标
            top_left_x = top_left_x + offset_x * ori_transform[1] + offset_y * ori_transform[2]
            top_left_y = top_left_y + offset_x * ori_transform[4] + offset_y * ori_transform[5]
            # 判断是否相交
            polygon_tmp = get_polygon(in_ds, top_left_x, top_left_y, block_xsize, block_ysize)
            poly1 = ogr.CreateGeometryFromWkt(polygon)
            poly2 = ogr.CreateGeometryFromWkt(polygon_tmp)
            intersection = poly1.Intersect(poly2)
            # pdb.set_trace()
            if not intersection:
                continue
            # 创建文件
            gtif_driver = gdal.GetDriverByName("GTiff")
            out_ds = gtif_driver.Create(out_path + '{}-{}.tif'.format(y, x), block_xsize, block_ysize, nb, bands_list[0].DataType)
            # 将计算后的值组装为一个元组，以方便设置
            dst_transform = (top_left_x, ori_transform[1], ori_transform[2], top_left_y, ori_transform[4], ori_transform[5])
            # 设置裁剪出来图的原点坐标
            out_ds.SetGeoTransform(dst_transform)
            # 设置SRS属性（投影信息）
            out_ds.SetProjection(in_ds.GetProjection())
            # 写入目标文件
            for i in range(1, nb + 1, 1):
                out_band_i = bands_list[i-1].ReadAsArray(offset_x, offset_y, block_xsize_tmp, block_ysize_tmp)
                m, n = out_band_i.shape
                if m != block_ysize or n != block_xsize:
                    out_band_i = np.pad(out_band_i,((0,block_ysize-m),(0,block_xsize-n)),'constant', constant_values = (0,0))
                out_ds.GetRasterBand(i).WriteArray(out_band_i)
            # 将缓存写入磁盘
            out_ds.FlushCache()
            print("flush cache success: {}-{}".format(y, x))
            del out_ds
    del in_ds

if __name__ == "__main__":
    tileclip('GF2_PMS1_E113.5_N35.5_20170401_L1A0002277643-MSS1.tiff', 'tiles/', 1024, 1024, 'POLYGON ((113.509955 35.4629505,113.555715 35.4629505,113.555715 35.49956585,113.509955 35.49956585,113.509955 35.4629505))')
    # tileclip('img.tif', 'tiles/', 1024, 1024, 'POLYGON ((113.509955 35.4629505,113.555715 35.4629505,113.555715 35.49956585,113.509955 35.49956585,113.509955 35.4629505))')