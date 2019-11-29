from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import pdb

def imagexy2geo(dataset, offsey_y, offset_x):
    trans = dataset.GetGeoTransform()
    px = trans[0] + offset_x * trans[1] + offsey_y * trans[2]
    py = trans[3] + offset_x * trans[4] + offsey_y * trans[5]
    return px, py

def get_polygon(origin_x, origin_y, offset_x, offset_y, w_e_pixel_resolution, n_s_pixel_resolution):
    new_x = origin_x + offset_x * w_e_pixel_resolution
    new_y = origin_y + offset_y * n_s_pixel_resolution
    polygon = 'POLYGON (('
    polygon += (str(origin_x) + ' ' + str(origin_y))
    polygon += (',' + str(new_x) + ' ' + str(origin_y))
    polygon += (',' + str(new_x) + ' ' + str(new_y))
    polygon += (',' + str(origin_x) + ' ' + str(new_y))
    polygon += (',' + str(origin_x) + ' ' + str(origin_y))
    polygon += '))'
    return polygon


def tileclip(file_path, out_path, block_xsize, block_ysize, polygon):
    # 读取要切的原图
    in_ds = gdal.Open(file_path)
    # 波段数
    nb = in_ds.RasterCount - 3
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
    # pdb.set_trace()
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
            polygon_tmp = get_polygon(top_left_x, top_left_y, block_xsize, block_ysize, w_e_pixel_resolution, n_s_pixel_resolution)
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