from pyproj import CRS

class CRS(CRS):
    @property
    def is_3d(self):
        return len(self.axis_info) == 3
