# Basics
import argparse

# Data
import numpy as np
import pandas as pd

# Country codes
import pycountry

# Rasters - pixel data
import rasterio
from rasterio.enums import Resampling

# Polygons - country outlines
from shapely.geometry import Polygon
import geopandas as gpd
from countryoutlines import CountryOutlines  # custom class

# Custom classes for Hansen et al., 2013
from hansenhandler import HansenHandler, DataType
from tile import Tile


def shrink(data, shape):
    to_rows, to_cols = shape
    from_rows, from_cols = data.shape
    assert from_rows % to_rows == 0
    row_shrink = from_rows//to_rows
    assert from_cols % to_cols == 0
    col_shrink = from_cols//to_cols

    return data.reshape(to_rows, row_shrink, to_cols, col_shrink).sum(axis=1).sum(axis=2) / (row_shrink * col_shrink)


def rescale(raster, resampling=Resampling.bilinear, upscale_factor=0.005):
    return raster.read(
        out_shape=(
            raster.count,
            int(raster.height * upscale_factor),
            int(raster.width * upscale_factor)
        ),
        resampling=resampling
    )


def read_band(raster, window=None, return_affine=False):
    if window:
        band = raster.read(1, window=window)
        affine = raster.window_transform(window)
    else:
        band = raster.read(1)
        affine = raster.transform

    if return_affine:
        return (band, affine)
    else:
        return band


def save_rescaled(coords):
    # https://data.ioos.us/dataset/tropic-of-cancer
    # https://data.ioos.us/dataset/tropic-of-capricorn
    cancer = 23.4394
    capricorn = -23.4394

    (lat_max, long_min) = coords
    lat_min = lat_max - 10
    if lat_max < capricorn or cancer < lat_min:
        return

    tile = Tile(*coords)
    fpath = f"{lat_max}_{long_min}"

    with tile.load_data(DataType.treecover2000) as cover_raster, \
        tile.load_data(DataType.datamask) as mask_raster, \
            tile.load_data(DataType.lossyear) as loss_raster:

        cover_rescaled = rescale(cover_raster)
        mask_rescaled = rescale(mask_raster)
        loss_rescaled = rescale(loss_raster)

        # old_transform = cover_raster.transform

        # # scale image transform
        # transform = cover_raster.transform * cover_raster.transform.scale(
        #     (cover_raster.width / cover_rescaled.shape[-1]),
        #     (cover_raster.height / cover_rescaled.shape[-2])
        # )

        profile = loss_raster.profile

        loss = loss_raster.read(1)

        for y in range(1, 21):

            with rasterio.open("temp.tif", "w", **profile) as temp:
                band = (loss == y).astype(float)
                temp.write(band, 1)
                del band

            with rasterio.open("temp.tif") as loss_new:
                lossy = rescale(loss_new, Resampling.average)

            np.save(f"{fpath}_loss_{y}.npy", lossy)

    np.save(f"{fpath}_cover.npy", cover_rescaled)
    np.save(f"{fpath}_mask.npy", mask_rescaled)
    np.save(f"{fpath}_loss.npy", loss_rescaled)
    del cover_rescaled, loss_rescaled, mask_rescaled, loss, lossy


n_splits = 21


def main(i_batch, debug):
    latlong = [(lat, long)
               for lat in range(-50, 90, 10)
               for long in range(-180, 180, 10)]

    n_tiles = len(latlong)

    split_size = n_tiles // (n_splits-1)

    splits = range(split_size, n_tiles, split_size)
    batches = np.split(latlong, splits)
    batch = batches[i_batch]

    for coords in batch:
        save_rescaled(coords)


def valid_index(arg):
    """Can be 0 to n_splits-1"""
    MIN_VAL = 0
    MAX_VAL = n_splits-1
    try:
        i = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("Must be an integer")
    if i < MIN_VAL or i > MAX_VAL:
        raise argparse.ArgumentTypeError(
            f"Argument must be < {MAX_VAL} and > {MIN_VAL}")
    return i


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('tile_index', type=valid_index,
                        help='tile index from 0 to 503')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    return args.tile_index, args.debug
    # 504


if __name__ == '__main__':
    args = parse_arguments()
    main(*args)
