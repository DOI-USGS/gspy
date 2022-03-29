
class key_mapping(dict):
    """ Handler class to user defined parameters. Allows us to check a users input parameters in the backend """
    
    def __init__(self, value, **kwargs):
        
        missing = [x for x in self.required_keys if not x in value]
        if len(missing) > 0:
            raise ValueError("Missing {} from the {} dict".format(missing, self.key))

        for key, value in value.items():
            self[key] = value

    @staticmethod
    def key(self):
        return 'key_mapping'
    
    @property
    def required_keys(self):
        return ('x',
                'y')