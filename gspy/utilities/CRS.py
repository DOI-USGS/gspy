from pyproj import CRS as pyproj_CRS

class CRS(pyproj_CRS):
    """pyproj's CRS with the one extra property GSPy needs."""

    @property
    def is_3d(self):
        return len(self.axis_info) == 3
