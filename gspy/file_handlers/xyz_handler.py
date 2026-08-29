from os.path import isfile
from .file_handler_abc import file_handler

class xyz_handler(file_handler, key='xyz'):
    """Shared base for the .xyz flavours

    Abstract: it defines no read, so it is not registered and cannot be
    dispatched to. Subclass it for a specific .xyz dialect.

    """
    extensions = ('.xyz',)

    @property
    def columns(self):
        return self.df.columns

    @property
    def type(self):
        return 'xyz'

    def metadata_template(self, **kwargs):
        out = super().metadata_template(**kwargs)
        out['variables'] = self.variable_metadata_template(**kwargs)

        return out

    @staticmethod
    def is_workbench(filename):
        with open(filename, 'r') as f:
            line = f.readline()
        return '/INFO' in line

    @staticmethod
    def is_workbench_model(filename):
        return isfile(filename[:-7]+"dat.xyz") & isfile(filename[:-7]+"inv.xyz") & isfile(filename[:-7]+"syn.xyz")
