
class variable_metadata(dict):
    """ Handler class to user defined parameters. Allows us to check a users input parameters in the backend """
    
    def __init__(self, **kwargs):
        
        for col in kwargs.keys():
            
            missing = [x for x in self.required_keys if not x in kwargs[col]]
            if len(missing) > 0:
                raise ValueError("Missing {} from {} in {} dict".format(missing, col, self.key))

        for key, value in kwargs.items():
            if key != "dimensions":
                self[key] = value
    
    @staticmethod
    def key(self):
        return 'units_and_nulls'

    @property
    def required_keys(self):
        return ('units',
                'standard_name',
                'long_name',
                'null_value'
                )