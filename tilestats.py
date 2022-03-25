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
from scripts.countryoutlines import CountryOutlines  # custom class

# Custom classes for Hansen et al., 2013
from scripts.hansenhandler import HansenHandler, DataType
from scripts.tile import Tile


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


def area_of_pixels(lat_start, lat_end, n_pixels):
    """Calculate m^2 area of an ndarray of wgs84 square pixels.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    """
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = np.sqrt(1 - (b/a)**2)
    lower = np.linspace(lat_start, lat_end, n_pixels, endpoint=False)

    higher = np.append(lower[1:], lat_end)
    pixel_size = (lat_end - lat_start) / n_pixels

    def subcalc(lats):
        sin_lats = np.sin(np.radians(lats))
        e_sin_lats = e*sin_lats
        zm = 1 - e_sin_lats
        zp = 1 + e_sin_lats
        return np.pi * b**2 * (np.arctanh(e_sin_lats) / e + sin_lats / (zp*zm))

    return pixel_size / 360. * (subcalc(higher) - subcalc(lower))


def make_table(coords) -> pd.DataFrame:

    # TODO add extra countries
    countries = np.array([[country.alpha_3, country.name]
                          for country in pycountry.countries])

    df = pd.read_csv("interim/country_bounds.csv", index_col=[0, 1])

    cancer = 23.4372
    capricorn = -23.4394
    tropics = Polygon([(-180, cancer), (-180, capricorn),
                       (180, capricorn), (180, cancer)])
    tropics = gpd.GeoDataFrame(geometry=[tropics])

    outlines = {country: None for country in df.country.unique()}

    win = None
    win = rasterio.windows.Window(20000, 20000, 20010, 20010)

    df[["code", "area", "cover_2000", "gain"]] = 0

    df[["lat", "long"]] = coords

    tile = Tile(*coords)
    # Subset countries whose bounds overlap
    countries = df[tile.covers_country(df)]

    # Check if no countries overlap
    if countries.empty:
        return df

    with tile.load_data(DataType.datamask) as mask_raster:
        mask, mask_affine = read_band(
            mask_raster, window=win, return_affine=True)

        # Check if the tile has no data
        # Might catch situations where country bounding box overlaps but country does not
        if not np.any(mask):
            return df

        area = np.ones(mask.shape)
        # TODO remove brackets
        with tile.load_data(DataType.treecover2000) as cover_raster, \
                tile.load_data(DataType.gain) as gain_raster:

            cover = read_band(cover_raster, window=win)
            cover[cover <= 25] = 0
            gain = read_band(gain_raster, window=win)

            countries = countries.droplevel("group")

            for c, row in countries.iterrows():
                # Load and save border if not already loaded
                country = row.country
                outline_gdf = outlines[country]
                if outline_gdf is None:
                    outlines[country] = outline_gdf = CountryOutlines.load_country(
                        c)

                geom = outline_gdf.geometry

                # Or start here
                geom = rasterize(geom, out_shape=mask.shape,
                                 transform=mask_affine)

                # Check if geom is empty
                if not np.any(geom):
                    print(c, tile.lat, tile.long)
                    continue

                # Either start here
                # c for country
                mask_c = mask * geom == 1
                area_c = area[mask_c]
                cover_c = cover[mask_c]
                # lossyear_c  = lossyear[mask_c]

                gain_c = gain[mask_c]

                df.loc[c, "area"].values[0] += area_c.sum()

                # Look into tensorflow one hot
                df.loc[c, "cover_2000"].values[0] += (cover_c * area_c).sum()

                df.loc[c, "gain"].values[0] += (gain_c * area_c).sum()

                # for year in range(1,20):
                #     yearmask = lossyear_c == year
                #     loss_cy = lossyear_c[yearmask]
                #     cover_cy = cover_c[yearmask]
                #     area_cy = area_c[yearmask]

                #     df.loc[c, f"loss_{year}"] += (loss_cy * cover_cy * area_cy).sum()
    return df


def main(i_tile):
    latlong = [(lat, long)
               for lat in range(-50, 90, 10)
               for long in range(-180, 180, 10)]

    coords = latlong[i_tile]
    df = make_table(coords)
    lat, long = coords
    df.to_csv(f"output/tile_stats_lat-{lat}_long-{long}.csv")


def valid_index(arg):
    """Can be 0 to 153"""
    MIN_VAL = 0
    MAX_VAL = 503
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
    parser.add_argument('tile_index', type=valid_index, nargs=1,
                        help='tile index from 0 to 153')
    args = parser.parse_args()
    return args.tile_index
    # 504


if __name__ == '__main__':
    args = parse_arguments()
    main(*args)
