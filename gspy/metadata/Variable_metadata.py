
class Variable_metadata(dict):
    """Handler class for user defined metadata. Allows us to check a users input parameters in the backend """

    def __init__(self, **kwargs):

        for col in kwargs.keys():

            missing = [x for x in self.required_keys if not x in kwargs[col]]
            if len(missing) > 0:
                raise ValueError(f"Missing {missing} from {col} in {self.key} dict")

            units = kwargs[col]['units']
            if '$' in units:
                kwargs[col]['units'] = r'{}'.format(units)

        for key, value in kwargs.items():
            if key != "dimensions":
                self[key] = value

    @staticmethod
    def key():
        return 'variables'

    @property
    def required_keys(self):
        return ('units',
                'standard_name',
                'long_name',
                'null_value'
                )
