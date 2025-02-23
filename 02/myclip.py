import gdal
import pdb
# 读取要切的原图
in_ds = gdal.Open("GF2_PMS1_E113.5_N35.5_20170401_L1A0002277643-MSS1.tiff")
# 波段数
nb = in_ds.RasterCount

# 读取原图中的每个波段
bands_list = []
for i in range(1, nb + 1, 1):
    bands_list.append(in_ds.GetRasterBand(i))

# 定义切图的大小（矩形框）
block_xsize = 512  # 行
block_ysize = 512  # 列

xpxs = in_ds.RasterXSize
ypxs = in_ds.RasterYSize

xcount = xpxs // block_xsize if xpxs % block_xsize == 0 else (xpxs // block_xsize) + 1
ycount = ypxs // block_ysize if ypxs % block_ysize == 0 else (ypxs // block_ysize) + 1

# pdb.set_trace()
for y in range(ycount):
    for x in range(xcount):
        offset_x = x * block_xsize
        offset_y = y * block_ysize
        # print('offset_x: {},offset_y: {}'.format(offset_x, offset_y))
        if (offset_x + block_xsize) > xpxs:
            block_xsize_tmp = xpxs - offset_x
        else:
            block_xsize_tmp = block_xsize
        if (offset_y + block_ysize) > ypxs:
            block_ysize_tmp = ypxs - offset_y
        else:
            block_ysize_tmp = block_ysize
        # print('block_xsize_tmp: {},block_ysize_tmp: {}'.format(block_xsize_tmp, block_ysize_tmp))
        # print('xx: {},yy: {}'.format(offset_x+block_xsize_tmp, offset_y+block_ysize_tmp))
        # out_band1 = in_band1.ReadAsArray(offset_x, offset_y, block_xsize_tmp, block_ysize_tmp)
        # out_band2 = in_band2.ReadAsArray(offset_x, offset_y, block_xsize_tmp, block_ysize_tmp)
        # out_band3 = in_band3.ReadAsArray(offset_x, offset_y, block_xsize_tmp, block_ysize_tmp)
        gtif_driver = gdal.GetDriverByName("GTiff")
        out_ds = gtif_driver.Create('tiles/{}-{}.tif'.format(y, x), block_xsize_tmp, block_ysize_tmp, nb, bands_list[0].DataType)
        ori_transform = in_ds.GetGeoTransform()
        # 读取原图仿射变换参数值
        top_left_x = ori_transform[0]  # 左上角x坐标
        w_e_pixel_resolution = ori_transform[1] # 东西方向像素分辨率
        top_left_y = ori_transform[3] # 左上角y坐标
        n_s_pixel_resolution = ori_transform[5] # 南北方向像素分辨率

        # 根据反射变换参数计算新图的原点坐标
        top_left_x = top_left_x + offset_x * w_e_pixel_resolution
        top_left_y = top_left_y + offset_y * n_s_pixel_resolution

        # 将计算后的值组装为一个元组，以方便设置
        dst_transform = (top_left_x, ori_transform[1], ori_transform[2], top_left_y, ori_transform[4], ori_transform[5])

        # 设置裁剪出来图的原点坐标
        out_ds.SetGeoTransform(dst_transform)

        # 设置SRS属性（投影信息）
        out_ds.SetProjection(in_ds.GetProjection())

        # 写入目标文件
        for i in range(1, nb + 1, 1):
            out_band_i = bands_list[i-1].ReadAsArray(offset_x, offset_y, block_xsize_tmp, block_ysize_tmp)
            out_ds.GetRasterBand(i).WriteArray(out_band_i)

        # 将缓存写入磁盘
        out_ds.FlushCache()
        print("FlushCache succeed")
        del out_ds