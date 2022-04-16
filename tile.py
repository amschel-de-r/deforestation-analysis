from hansenhandler import HansenHandler, DataType
import rasterio
import pandas as pd


class Tile:
    def __init__(self, lat, long):
        self.lat = lat
        self.latRange = pd.Interval(lat-10, lat)
        self.long = long
        self.longRange = pd.Interval(long, long+10)
        self.hh = HansenHandler

    def get_url(self, dType: DataType):
        return self.hh.geturlpath(dType, self.lat, self.long)
    
    def get_filepath(self, dtype: DataType):
        return self.hh.getfilepath(dtype, self.lat, self.long)

    def load_data(self, dType: DataType, fromfile=False) -> rasterio.DatasetReader:
        url = self.get_url(dType) if not fromfile else self.get_filepath(dType)
        return rasterio.open(url)

    def covers_country(self, df: pd.DataFrame):
        df_lat = pd.arrays.IntervalArray.from_arrays(df.miny, df.maxy, closed="left")
        df_long = pd.arrays.IntervalArray.from_arrays(df.minx, df.maxx, closed="left")

        return df_lat.overlaps(self.latRange) & df_long.overlaps(self.longRange)
