from enum import Enum
import re


class DataType(Enum):
    treecover2000 = "treecover2000"
    lossyear = "lossyear"
    gain = "gain"
    datamask = "datamask"


class HansenHandler:

    # Hansen_GFC-2020-v1.8_lossyear_00N_060W.tif
    # TODO make multiline with comments?
    # TODO check for other data
    pattern = r'Hansen_GFC-\d+-v[\d\.]+_([\w\d]+)_(\d\d[NS])_(\d\d\d[WE]).tif'
    matcher = re.compile(pattern)

    def __init__(self, filename) -> None:
        m = HansenHandler.matcher.match(filename)
        self.var, self.long, self.lat = m.groups()
        self.filename = filename

    @classmethod
    def getfilepath(cls, dtype: DataType, lat, long):
        datadir = "raw"
        filename = cls.getfilename(dtype, lat, long)
        return f"{datadir}/{filename}"

    @classmethod
    def geturlpath(cls, dtype: DataType, lat, long):
        urlstub = "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2020-v1.8"
        filename = cls.getfilename(dtype, lat, long)
        return f"{urlstub}/{filename}"

    @classmethod
    def getfilename(cls, dtype: DataType, lat, long):
        lat_str = cls.lat_num2str(lat)
        long_str = cls.long_num2str(long)
        return f"Hansen_GFC-2020-v1.8_{dtype.value}_{lat_str}_{long_str}.tif"

    @classmethod
    def long_num2str(cls, num):
        """Converts numbers to latitude strings, e.g. -20 --> 020W"""
        EW = "W" if num < 0 else "E"
        return f"{abs(num):03d}{EW}"

    @classmethod
    def long_str2num(cls, lat):
        """Converts latitude strings to numbers, e.g. 020W --> -20"""
        pattern = r'(\d+)([EW])'
        match = re.match(pattern, lat)
        sign = -1 if match.groups[2] == "W" else 1
        return int(match.groups[1]) * sign

    @classmethod
    def lat_num2str(cls, num):
        """Converts numbers to longitude strings, e.g. -20 --> 20S"""
        NS = "S" if num < 0 else "N"
        return f"{abs(num):02d}{NS}"

    @classmethod
    def lat_str2num(cls, long):
        """Converts longitude strings to numbers, e.g. 20S --> -20"""
        pattern = r'(\d+)([NS])'
        match = re.match(pattern, long)
        sign = -1 if match.groups[2] == "S" else 1
        return int(match.groups[1]) * sign
