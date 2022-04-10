# Basics
import argparse

# Data
import numpy as np
import pandas as pd

# Country codes
import pycountry

# Rasters - pixel data
import rasterio
from rasterio.features import rasterize

# Polygons - country outlines
from shapely.geometry import Polygon
import geopandas as gpd
from countryoutlines import CountryOutlines  # custom class

# Custom classes for Hansen et al., 2013
from hansenhandler import HansenHandler, DataType
from tile import Tile


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


def latitude_square_area_matrix(lat_min, lat_max, pixels_per_side):
    """Calculate m^2 area of an ndarray of wgs84 square pixels.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    """
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = np.sqrt(1 - (b/a)**2)

    higher = np.linspace(lat_max, lat_min, pixels_per_side, endpoint=False)
    lower = np.append(higher[1:], lat_min)

    pixel_size = (lat_max - lat_min) / pixels_per_side

    def subcalc(lats):
        sin_lats = np.sin(np.radians(lats))
        e_sin_lats = e*sin_lats
        zm = 1 - e_sin_lats
        zp = 1 + e_sin_lats
        return np.pi * b**2 * (np.arctanh(e_sin_lats) / e + sin_lats / (zp*zm))

    col = pixel_size / 360. * (subcalc(higher) - subcalc(lower))
    return np.tile(col.reshape((-1, 1)), pixels_per_side)


def make_table(coords, debug=False) -> pd.DataFrame:
    df = pd.read_csv("interim/country_bounds.csv")

    outlines = {code: None for code in df.code.unique()}

    def get_geom(code):
        outline_gdf = outlines[code]
        if outline_gdf is None:
            outlines[code] = outline_gdf = CountryOutlines.load_country(code)
        return outline_gdf.geometry[0]

    df[["lat", "long"]] = (lat_max, long_min) = coords
    lat_min = lat_max - 10

    if debug:
        total_side = 40000
        offset = total_side / 2
        side_length = 2
        win = rasterio.windows.Window(offset, offset, side_length, side_length)
        win = rasterio.windows.Window(20000, 20000, 5, 1)
        lat_min = (lat_max-lat_min)*offset/total_side
        lat_max = lat_min + side_length/total_side
    else:
        win = None

    tile = Tile(*coords)
    # Subset countries whose bounds overlap
    df = df[tile.covers_country(df)]

    # Check if no countries overlap
    if df.empty:
        print("No country bounds overlap tile")
        return df

    # https://data.ioos.us/dataset/tropic-of-cancer
    # https://data.ioos.us/dataset/tropic-of-capricorn
    cancer = 23.4394
    capricorn = -23.4394

    def ilat(lat):
        return round((10 - lat % 10) * 4000) - 1

    if lat_max < capricorn or cancer < lat_min:
        tropicTop = tropicBottom = None
    else:
        # Going from north to south
        tropicTop = ilat(cancer) if cancer < lat_max else 0
        tropicBottom = ilat(capricorn)+1 if lat_min < capricorn else 40000

    df = pd.concat([df.copy().assign(tropics=tropics) for tropics in (False, True)], ignore_index=True)
    df = df.sort_values(by=["code", "tropics"]).reset_index(drop=True)

    with tile.load_data(DataType.datamask) as mask_raster:
        mask, mask_affine = read_band(mask_raster, window=win, return_affine=True)

        # Check if the tile has no data
        # Might catch situations where country bounding box overlaps but country does not
        if not np.any(mask):
            print("No datapoints in tile")
            return df

        country_codes = df.loc[::2, "code"].iteritems()

        geom = rasterize([(get_geom(code), i) for i, code in country_codes],
                         out_shape=mask.shape, fill=-2, transform=mask_affine)

        if not np.any(geom):
            print("No countries overlap tile")
            return df

        if tropicTop:
            geom[tropicTop:tropicBottom, :] += 1

        area = latitude_square_area_matrix(lat_min, lat_max, mask.shape[0])

        mask = (mask == 1) & (geom >= 0)
        geom = geom[mask]
        area = area[mask]

        with tile.load_data(DataType.treecover2000) as cover_raster, \
                tile.load_data(DataType.lossyear) as loss_raster:
            # tile.load_data(DataType.gain) as gain_raster, \

            cover = read_band(cover_raster, window=win)
            cover = cover[mask]

            # gain = read_band(gain_raster, window=win)
            lossyear = read_band(loss_raster, window=win)
            lossyear = lossyear[mask]
            pos = cover > 0
            cover_cat = cover
            cover_cat[pos] = (cover[pos] - 1) // 25 + 1
            df = pd.concat([df.copy().assign(cover_cat=cc)
                            for cc in ["0", "1-25", "26-50", "51-75", "76-100"]], ignore_index=True)
            df = df.sort_values(by=["code", "tropics", "cover_cat"]).reset_index(drop=True)

            print(np.unique(cover_cat))
            geom_cat = geom * 5 + cover_cat
            del geom, cover_cat

            nrows = df.shape[0]

            df["pixels"] = np.bincount(geom_cat, minlength=nrows)
            df["area"] = np.bincount(geom_cat, weights=area, minlength=nrows)

            area_cover = area*cover
            del area, cover
            df["cover_2000"] = np.bincount(geom_cat, weights=area_cover, minlength=nrows)

            geom_cat = geom_cat * 21 + lossyear
            loss = np.bincount(geom_cat, weights=area_cover, minlength=nrows*21)
            loss = loss.reshape((-1, 21))[:, 1:]

            lossyear_labels = [f"loss_20{year+1}" for year in range(20)]
            df[[*lossyear_labels]] = loss
    return df


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
        df = make_table(coords, debug)
        lat, long = coords
        lat_str = HansenHandler.lat_num2str(lat)
        long_str = HansenHandler.long_num2str(long)
        df.to_csv(f"output/tile_stats_{lat_str}_{long_str}.csv")


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
