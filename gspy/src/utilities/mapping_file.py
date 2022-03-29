# importing the module
import json

# The mapping class takes a user written json file and maps original column headers to the standardised names.

class mapping(object):

    def __init__(self, filename, required_fields):

        self.required = required_fields

        if isinstance(filename, str):
            self.map = self.read(filename) # figure out how to do this part.
        elif isinstance(filename, dict):
            self.map = filename
        else:
            assert False, TypeError('filename must have type str or dict')

    def __getitem__(self, key):
        return self.map[key]

    def __contains__(self, key):
        return key in self.map

    @property
    def map(self):
        return self._map

    @map.setter
    def map(self, value):

        for x in self.required:
            assert x in value, ValueError("Mapping must have the following entries {}".format(self.required))


        assert all([isinstance(value[x], str) for x in self.required]), ValueError("Mapping entries must have type str.")

        self._map = value


    def read(self, filename):
        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        # reconstructing the data as a dictionary
        return json.loads(s)
