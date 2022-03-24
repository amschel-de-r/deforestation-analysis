import geopandas as gpd
import pycountry
import urllib.error
import pandas as pd
import numpy as np


class CountryOutlines:
    @classmethod
    def get_url(cls, country_alpha3):
        siteroot = "https://geodata.ucdavis.edu/gadm/gadm4.0/gpkg/gadm40_"
        return f"{siteroot}{country_alpha3}.gpkg"

    @classmethod
    def load_country(cls, country_alpha3):
        filepath = cls.get_url(country_alpha3)
        return gpd.read_file(filepath)

    @classmethod
    def get_bounds(cls, code, country=None) -> pd.DataFrame:
        country = country or pycountry.countries.get(alpha_3=code).name

        try:
            gdf = cls.load_country(code)
            df = gdf.geometry.bounds
            if df.minx[0] < -160 and df.maxx[0] > 160 and code != "ATA":
                gdf = gdf.explode()
                df = gdf.geometry.bounds
                df["group"] = np.where(df.minx < 0, 1, 2)
                df = df.groupby("group").agg(
                    minx=("minx", "min"),
                    miny=("miny", "min"),
                    maxx=("maxx", "max"),
                    maxy=("maxy", "max")
                )
                df = df.reset_index(level="group")
            else:
                df["group"] = 1
            del gdf  # to save memory
            df["code"] = code
            df["country"] = country
            return df
        except urllib.error.HTTPError:
            print(
                f"No file found for {code}: {pycountry.countries.get(alpha_3=code).name}")
            return pd.DataFrame(columns=["group", "minx", "miny", "maxx", "maxy", "code", "country"])
