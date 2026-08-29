import os
from pathlib import Path
from pprint import pprint
import numpy as np
import xarray as xr
from ..utilities import unique_list_preserve, same_length_lists
from ..metadata.Metadata import Metadata
from ..metadata.Variable_metadata import Variable_metadata
# from ..gs_dataarray.DataArray import DataArray
from .Dataset import Dataset

class System(Dataset):
    required_metadata = ('type',
                     'mode',
                     'method',
                     'instrument')

    @classmethod
    def _template_directory(cls):
        """Where the bundled system templates live.

        One spec per method family. Each names the fields that method uses and
        the thing each field is repeated for; the shape comes from the caller.

        Resolved on call rather than at import so the builder's absolute path is
        never baked into a class attribute (Sphinx renders those into the docs).

        Returns
        -------
        pathlib.Path

        """
        return Path(__file__).parents[1] / 'metadata' / 'system_templates'

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def is_projected(self):
        return False

    # @property
    # def attrs(self):
    #     return self._obj.attrs

    # @attrs.setter
    # def attrs(self, values:dict):
    #     assert isinstance(values, dict), TypeError("attrs must have type dict")
    #     self._obj.attrs = self._obj.attrs | values

    def check_against_data(self, dataset):
        """Assert that gate time strings match the coordinates of the attached dataset.
        """
        for gt in self._obj['couplet_gate_times']:
            assert gt in list(dataset.coords.keys()), ValueError(f"Could not match couplet gate times {gt} to dataset coordinates")

    @classmethod
    def templates(cls):
        """The method families that ``metadata_template`` can shape a template for.

        Returns
        -------
        tuple of str

        """
        return tuple(sorted(p.stem for p in cls._template_directory().glob('*.yml')))

    @classmethod
    def metadata_template(cls, key, name=None, transmitters=None, receivers=None, metadata=None):
        """A metadata template for one system, shaped to its transmitters and receivers.

        Parameters
        ----------
        key : str
            Which method family to template, one of :meth:`templates`.
        name : str, optional
            What to file the system under, ``f"{key}_system"`` by default. Must
            contain "system", because that is what a container looks for when it
            lifts system definitions out of a dataset's metadata.
        transmitters, receivers : int or list of str, optional
            How many of each there are, or their labels. A count gives indexed
            labels. Both default to one. Where a family pairs its transmitters and
            receivers one to one, giving only one side mirrors it onto the other.
        metadata : dict, optional
            What you already know about this system. Wins over the placeholders.

        Returns
        -------
        gspy.Metadata
            ``{name: the system}``, ready to merge into a dataset's metadata.

        Notes
        -----
        Fields are repeated to match the shape asked for, and collapse to a single
        value where there is only one of something. Couplets are worked out from the
        two sets of labels: every receiver measures every transmitter, unless the
        family pairs them off, and anything named per transmitter - time domain gate
        times, say - is named after the transmitter label it belongs to.

        A template is a skeleton, not a system. Its dimensions hold placeholders
        where real gate times or frequencies go, so it will not build until those
        are filled in, the same way ``Survey.metadata_template`` does not yield a
        coordinate reference system from ``wkid: '??'``.

        Examples
        --------
        Two moments read by two coils, so four couplets:

        >>> System.metadata_template('tdem', name='skytem_system',
        ...                          transmitters=['LM', 'HM'], receivers=['z', 'x'])

        Six frequencies, each coil pair its own couplet:

        >>> System.metadata_template('fdem', transmitters=6)

        """
        spec = cls._template_spec(key)
        paired = spec.get('pairing') == 'paired'
        labels = spec.get('labels', {})

        # Where they pair off, a transmitter and its receiver are the same coil pair,
        # so one set of labels describes both and either side can supply it.
        if paired and (transmitters is None or receivers is None):
            given = transmitters if transmitters is not None else receivers
            transmitters = receivers = cls._template_labels(given, 'transmitter', labels)

        transmitters = cls._template_labels(transmitters, 'transmitter', labels)
        receivers = cls._template_labels(receivers, 'receiver', labels)

        if paired and len(transmitters) != len(receivers):
            raise ValueError(f"The transmitters and receivers of a {key} system pair up one to one, "
                             f"so {len(transmitters)} transmitters cannot be given {len(receivers)} receivers")

        # Every receiver measures every transmitter, receiver slowest, which is the
        # order the couplets of a dual moment system are conventionally listed in.
        couplets = list(zip(transmitters, receivers)) if paired \
            else [(t, r) for r in receivers for t in transmitters]

        name = f"{key}_system" if name is None else name
        if 'system' not in name:
            raise ValueError(f"A system must be named with 'system' in it, so '{name}' would not be "
                             "recognised as one when the metadata is read back")

        dimensions, per_transmitter = {}, []
        for dimension, values in spec.get('dimensions', {}).items():
            values = dict(values)
            if values.pop('per', None) != 'transmitter':
                dimensions[dimension] = values
                continue

            per_transmitter.append(dimension)
            for label in transmitters:
                named = cls._template_dimension(dimension, label, transmitters)
                dimensions[named] = {'standard_name': named} | \
                    {k: v.format(label=label) if isinstance(v, str) and '{label}' in v else v
                     for k, v in values.items()}

        variables = dict(spec['variables'].get('scalars', {}))
        variables['transmitter'] = cls._template_block(spec['variables']['transmitter'], transmitters)
        variables['receiver'] = cls._template_block(spec['variables']['receiver'], receivers)
        variables['couplet'] = cls._template_couplets(spec['variables']['couplet'], couplets,
                                                      transmitters, per_transmitter)
        variables.update(spec.get('prefixes', {}))

        system = Metadata(spec['attrs'])
        if spec.get('prefixes'):
            system['prefixes'] = list(spec['prefixes'])
        system['dimensions'] = dimensions
        system['variables'] = variables

        return Metadata({name: Metadata.merge(system, metadata if metadata is not None else {})})

    @classmethod
    def _template_spec(cls, key):
        """The field spec for a method family, by short key."""
        path = cls._template_directory() / f"{key}.yml"
        if not path.exists():
            raise ValueError(f"No system template called '{key}'. Choose one of {cls.templates()}")

        spec = Metadata.read(str(path))
        spec.pop('directory', None)
        return spec

    @staticmethod
    def _template_labels(labels, prefix, defaults):
        """Labels for a prefix, from the labels themselves or from how many there are.

        A count falls back to the family's own labels where it asks for exactly as
        many as the family has - one passive transmitter, for a magnetometer - and to
        indexed labels otherwise.

        """
        if isinstance(labels, str):
            return [labels]

        if not isinstance(labels, (int, type(None))):
            return list(labels)

        count = 1 if labels is None else labels
        if count < 1:
            raise ValueError(f"A system needs at least one {prefix}, not {count}")

        default = defaults.get(prefix, [])
        if len(default) == count:
            return list(default)

        return [f"{prefix}_{i + 1}" for i in range(count)]

    @staticmethod
    def _template_dimension(dimension, label, transmitters):
        """A per transmitter dimension is named after the transmitter it belongs to.

        With one transmitter there is nothing to tell apart, so it keeps its bare
        name - the way every single moment example writes it.

        """
        return dimension if len(transmitters) == 1 else f"{label}_{dimension}".lower()

    @classmethod
    def _template_block(cls, fields, labels):
        """One prefix of a system: its labels, and every field repeated to match."""
        out = Metadata(label=cls._template_repeat_to(labels))
        for field, value in fields.items():
            out[field] = cls._template_repeat(value, len(labels))
        return out

    @classmethod
    def _template_couplets(cls, fields, couplets, transmitters, per_transmitter):
        """The couplets, with their pairing and their per transmitter fields filled in.

        Nothing here collapses to a single value: ``transmitters`` and ``receivers``
        are read as lists when the couplet labels are put together, and a lone string
        would be read a character at a time.

        """
        out = Metadata(transmitters=[t for t, _ in couplets],
                       receivers=[r for _, r in couplets])

        for field, value in fields.items():
            if field in out:
                continue
            if field in per_transmitter:
                out[field] = [cls._template_dimension(field, t, transmitters) for t, _ in couplets]
            else:
                out[field] = [value] * len(couplets)

        return out

    @classmethod
    def _template_repeat(cls, value, count):
        """A placeholder, once per thing it describes.

        A field given as a dict is left alone: it carries its own ``dimensions``, or
        its ``values`` hold the whole array, so only the placeholder inside it repeats.

        """
        if isinstance(value, dict):
            if 'values' in value and 'dimensions' not in value:
                return dict(value) | {'values': cls._template_repeat(value['values'], count)}
            return dict(value)

        return cls._template_repeat_to([value] * count)

    @staticmethod
    def _template_repeat_to(values):
        """One of something is a value, more than one is a list of them."""
        return values[0] if len(values) == 1 else list(values)

    @classmethod
    def open(cls, filename, **kwargs):
        md = Metadata.read(filename)
        for key,item in md.items():
            out = cls.from_dict(**item)
        return out

    @classmethod
    def from_dict(cls, **kwargs):

        kwargs = Metadata(kwargs)

        attrs, kwargs = kwargs.pop_and_split(cls.required_metadata)

        self = cls(xr.Dataset(attrs=attrs))

        for key, value in kwargs.pop('dimensions', {}).items():
            self._obj = self._obj.gs.add_coordinate_from_dict(key.lower(),
                                                 is_dimension=True,
                                                 **value)

        required_prefixes = ['transmitter', 'receiver', 'couplet']

        prefixes =  unique_list_preserve(required_prefixes + kwargs.pop('prefixes', []))

        assert 'variables' in kwargs, ValueError("Missing variables section for system")
        assert all([x in kwargs['variables'] for x in required_prefixes]), ValueError("transmiter, receiver, couplet must be contained in the variables")

        if 'variables' in kwargs:
            for prefix in prefixes:
                vars = kwargs['variables']
                if prefix == 'couplet' and 'couplet' in vars:
                    if 'label' not in vars['couplet'].keys():
                        vars['couplet'] = self.__couplet_labels(**vars['couplet'])
                    if 'gate_times' in vars['couplet']:
                        vars['couplet']['gate_times'] = [x.lower() for x in vars['couplet']['gate_times']]

                self, kwargs['variables'] = self.__add_using_prefix(prefix, **kwargs['variables'])

            for key, values in kwargs['variables'].items():
                if not isinstance(values, dict):
                    values = dict(values=values)
                self._obj = self._obj.gs.add_variable_from_dict(name=key, check=False, **values)
            kwargs.pop('variables')

        # Cannot have literal Booleans in the attributes of a netcdf...
        # Convert to strings...
        for k, v in kwargs.items():
            if isinstance(v, bool):
                kwargs[k] = "True" if v else "False"

        self._obj.attrs = self._obj.attrs | kwargs

        return self._obj

    def __couplet_labels(self, **kwargs):
        kwargs['label'] = kwargs.get('receivers')
        if 'transmitters' in kwargs:
            kwargs['label'] = [f"{a}_{b}" for a, b in zip(kwargs['transmitters'], kwargs['label'])]
        return kwargs

    def __add_using_prefix(self, prefix, **kwargs):

        if prefix not in kwargs:
            return self, kwargs

        popped = kwargs.pop(prefix)

        label = popped.pop('label', None)
        if isinstance(label, dict):
            label = label['values']

        if len(popped) > 1:
            assert label is not None, ValueError(f"metadata for {prefix} given but no labels")

        if isinstance(label, str):
            label = [label]

        n_entries = np.size(label)

        self._obj = self.add_coordinate_from_values(f"n_{prefix}",
                                                values=np.arange(n_entries),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = f"number_of_{prefix}s",
                                                        long_name = f"Number of {prefix}s",
                                                        units = "not_defined",
                                                        missing_value = "not_defined"))

        self, popped = self.add_dimensions_from_variables(prefix=prefix, label=label, **popped)
        popped.pop('prefix', None)
        for key, values in popped.items():
            if not isinstance(values, dict):
                if not isinstance(values, list):
                    values = np.full(n_entries, fill_value=values)
                values = dict(values=values)
            values['dimensions'] = values.pop('dimensions', f"n_{prefix}")
            self._obj = self._obj.gs.add_variable_from_dict(name=key, label=label, check=False, prefix=prefix, **values)

        return self, kwargs

    @classmethod
    def valid_model(cls, **kwargs):
        return kwargs["mode"] in ("airborne", "waterborne", "ground", "borehole")

    @classmethod
    def valid_method(cls, **kwargs):
        return kwargs["method"] in ("electromagnetic", "magnetic", "gravity", "galvanic", "nmr")

    @classmethod
    def valid_instrument(cls, **kwargs):
        return any(x in kwargs["instrument"] for x in ('resolve', 'skytem', 'tempest', 'cesium vapour'))
