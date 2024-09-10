from numpy import sin, cos, sqrt, atan2, radians
def haversine_distance(lon0, lat0, lon1, lat1):
	dlon = radians(lon1) - radians(lon0)
	dlat = radians(lat1) - radians(lat0)
	a = sin(dlat / 2)**2 + cos(radians(lat0)) * cos(radians(lat1)) * sin(dlon / 2)**2
	return 6373000.0 * 2 * atan2(sqrt(a), sqrt(1 - a))
