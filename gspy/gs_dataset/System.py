import os
from copy import deepcopy
from pathlib import Path
from pprint import pprint
import numpy as np
import xarray as xr
from ..utilities import unique_list_preserve, same_length_lists
from ..metadata.Metadata import Metadata
from ..metadata._stm_md_handler import read_stm
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

        out = Metadata({name: Metadata.merge(system, metadata if metadata is not None else {})})
        out.comments = cls._template_comments(spec.comments, name, transmitters, per_transmitter)
        return out

    @classmethod
    def _template_comments(cls, comments, name, transmitters, per_transmitter):
        """The template's comments, moved to where its fields end up in the system.

        The header goes above the system, attributes are lifted to its top level,
        scalars and prefixes into its variables, and a per transmitter dimension's
        comment is copied to each transmitter's.

        """
        out = {}
        for path, comment in comments.items():
            head, rest = path[:1], path[1:]
            if path == ():
                out[(name,)] = comment
            elif head == ('attrs',) and rest:
                out[(name, *rest)] = comment
            elif head == ('dimensions',) and rest and rest[0] in per_transmitter:
                for label in transmitters:
                    named = cls._template_dimension(rest[0], label, transmitters)
                    labelled = lambda text: text.replace('{label}', label)
                    out[(name, 'dimensions', named, *rest[1:])] = \
                        {k: [labelled(line) for line in v] if k == 'above' else labelled(v)
                         for k, v in comment.items()}
            elif head in (('dimensions',), ('variables',)) and rest != ('scalars',):
                if rest[:1] == ('scalars',):
                    rest = rest[1:]
                out[(name, *head, *rest)] = comment
            elif head == ('prefixes',) and rest:
                out[(name, 'variables', *rest)] = comment
        return out

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

    # A .stm says which domain it is in two different ways, and sometimes neither.
    __stm_domains = {'time': 'tdem', 'tdem': 'tdem', 'time domain': 'tdem',
                     'frequency': 'fdem', 'fdem': 'fdem', 'frequency domain': 'fdem'}

    @classmethod
    def from_stm(cls, stm, **kwargs):
        """A system built from a GA-AEM .stm file.

        Takes the same arguments as :meth:`metadata_from_stm` and builds what it
        returns. A time domain .stm carries its own gate times and waveform, so this
        yields a system on its own; pass the rest in ``metadata`` to fill in what the
        file cannot say.

        Returns
        -------
        xarray.Dataset

        """
        return cls.from_dict(**next(iter(cls.metadata_from_stm(stm, **kwargs).values())))

    @classmethod
    def metadata_from_stm(cls, stm, domain=None, name=None, receivers=None, metadata=None):
        """System metadata read from a GA-AEM .stm file, over a template.

        Parameters
        ----------
        stm : str or dict
            The file, or ``{transmitter label: file}`` where a moment is a file of its
            own. The labels are the transmitters, in the order given.
        domain : str, optional
            'time' or 'frequency', where the file does not say or says wrongly.
            Worked out from the file by default.
        name : str, optional
            What to file the system under, as in :meth:`metadata_template`.
        receivers : int or list of str, optional
            The receivers. Taken from which components the file scales by default.
        metadata : str or dict, optional
            What you already know, or the yml holding it. Wins over the file. A yml
            written as one ``<name>_system:`` entry is unwrapped, and names the system.

        Returns
        -------
        gspy.Metadata
            ``{name: the system}``, ready to build, or to dump and fill in.

        Notes
        -----
        A .stm is a forward modelling file, not a system description, so what it can
        answer it answers and the rest is left as template placeholders. It models an
        airborne dipole, so the mode is airborne and there is no loop geometry to ask
        for. The loop is kept per transmitter, a placeholder for one whose file does not
        say; GA-AEM has no default for NumberOfTurns. The moment is turns x area x peak
        current, of the loop the system ends up with once the yml is merged. The file
        is often a unit loop the forward model scaled out, so ``data_normalized`` is
        judged by the file's own loop and normalisation: a unit moment or ppm means
        normalised, a real moment means not. Where the files disagree, it is yours.
        Anything read that GSPy has no field for is recorded in the attributes under
        ``stm_``, so nothing in the file is lost.

        Examples
        --------
        A moment per file, read by two coils:

        >>> System.from_stm({'LM': 'SkytemLM.stm', 'HM': 'SkytemHM.stm'},
        ...                 receivers=['z', 'x'], metadata='skytem_system.yml')

        Or dump what the file knows and fill in the rest by hand:

        >>> System.metadata_from_stm('Tempest.stm').dump('tempest_system.yml')

        """
        files = {label: str(path) for label, path in stm.items()} if isinstance(stm, dict) \
            else {None: str(stm)}
        read = {label: read_stm(path) for label, path in files.items()}

        key = cls.__stm_domain(domain, read)
        name, given = cls.__stm_given(name, metadata)

        reader = cls.__stm_time_domain if key == 'tdem' else cls.__stm_frequency_domain
        found, transmitters, receivers = reader(files, read, receivers)

        template = cls.metadata_template(key, name=name, transmitters=transmitters,
                                         receivers=receivers)
        name = next(iter(template))
        system = template[name]

        if key == 'tdem':
            # A dipole approximation has no loop, so there are no vertices to ask for.
            # Dropped rather than left placeheld, and a yml can still put them back.
            for held in ('n_loop_vertices', 'xyz'):
                system['dimensions'].pop(held, None)
            system['variables']['transmitter'].pop('coordinates', None)

        system = cls.__stm_over(cls.__stm_over(system, found), given)
        if key == 'tdem':
            cls.__stm_remoment(system['variables']['transmitter'],
                               given.get('variables', {}).get('transmitter', {}))

        return Metadata({name: Metadata(system)})

    @classmethod
    def __stm_domain(cls, domain, read):
        """Which method family a .stm is templated as."""
        if domain is not None:
            key = cls.__stm_domains.get(str(domain).strip().lower())
            if key is None:
                raise ValueError(f"A .stm holds a time domain or a frequency domain system, so "
                                 f"domain must be one of {sorted(cls.__stm_domains)}, not '{domain}'")
            return key

        if len({stm['format'] for stm in read.values()}) > 1:
            raise ValueError("The files given are not all the same kind of .stm, so they cannot "
                             "be the moments of one system")

        if all(stm['format'] == 'table' for stm in read.values()):
            return 'fdem'

        return 'fdem' if all('frequency' in str(stm.get('type', '')).lower()
                             for stm in read.values()) else 'tdem'

    @staticmethod
    def __stm_given(name, metadata):
        """What the caller already knows, and the name it files the system under."""
        given = Metadata.read(metadata) if metadata is not None else Metadata()
        given.pop('directory', None)

        if len(given) == 1:
            only = next(iter(given))
            if 'system' in only and isinstance(given[only], dict):
                return (only if name is None else name), given[only]

        return name, given

    @classmethod
    def __stm_over(cls, template, found):
        """``found`` over ``template``, all the way down.

        Metadata.merge stops at the second level, which would swap a whole
        transmitter block for the handful of its fields a .stm can answer.

        """
        out = deepcopy(dict(template))
        for key, value in found.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = cls.__stm_over(out[key], value)
            else:
                out[key] = deepcopy(value)
        return out

    @classmethod
    def __stm_time_domain(cls, files, read, receivers):
        """What a block .stm says about a time domain system."""
        for path, stm in zip(files.values(), read.values()):
            if stm['format'] != 'block':
                raise ValueError("A time domain system is read from a 'System Begin' block, "
                                 f"but {path} is a csv table of coil pairs")

        # Read from a copy: what is taken is popped, and what is left over at the end
        # is what the file said that GSPy has no field for.
        blocks = {label: deepcopy(stm) for label, stm in read.items()}
        for stm in blocks.values():
            for consumed in ('format', 'type'):
                stm.pop(consumed, None)

        labels = None if None in blocks else list(blocks)
        transmitters = cls._template_labels(labels, 'transmitter', {})

        components = cls.__stm_components(blocks)
        if receivers is None:
            receivers = components
        receivers = cls._template_labels(receivers, 'receiver', {})

        dimensions, transmitter, couplet = {}, {}, {}
        times, currents, stated, normalisations = [], [], {}, []

        for label, path, stm in zip(transmitters, files.values(), blocks.values()):
            named = cls._template_dimension('gate_times', label, transmitters)
            dimensions[named] = cls.__stm_gates(named, label, transmitters, path, stm)

            waveform = stm.get('transmitter', {}).pop('waveform_current', None)
            if waveform is None:
                raise ValueError(f"{path} has no WaveFormCurrent, so it does not say what the "
                                 "transmitter did")
            times.append([time for time, _ in waveform])
            currents.append([current for _, current in waveform])
            normalisations.append(stm.get('forward_modelling', {})
                                  .get('secondary_field_normalisation'))

            for field, block, key in (('base_frequency', 'transmitter', 'base_frequency'),
                                      ('digitization_frequency', 'transmitter',
                                       'waveform_digitising_frequency'),
                                      ('number_of_turns', 'transmitter', 'number_of_turns'),
                                      ('peak_current', 'transmitter', 'peak_current'),
                                      ('area', 'transmitter', 'loop_area'),
                                      ('output_data_type', 'forward_modelling', 'output_type')):
                stated.setdefault(field, (block, key, []))[2].append(
                    stm.get(block, {}).get(key))

        times, currents = cls.__stm_waveform(times, currents)
        transmitter['waveform_time'] = {'values': times}
        transmitter['waveform_current'] = {'values': currents}
        # A block .stm models a horizontal loop, which is a vertical dipole. Nowhere in
        # the file says so, the format does.
        transmitter['orientation'] = cls._template_repeat_to(['z'] * len(transmitters))

        variables = {'transmitter': transmitter, 'couplet': couplet}
        if components == cls._template_labels(components, 'receiver', {}) == receivers:
            variables['receiver'] = {'orientation': cls._template_repeat_to(list(receivers))}

        # Each couplet is read from its own transmitter, so the data type is per couplet
        # even where the moments were modelled as different quantities.
        block, key, types = stated['output_data_type']
        types = [None if value is None else cls.__stm_data_type(value, normalisation)
                 for value, normalisation in zip(types, normalisations)]
        stated['output_data_type'] = (block, key, types)
        if all(value is not None for value in types):
            couplet['data_type'] = [types[t] for _ in receivers for t in range(len(transmitters))]

        placeholders = cls._template_spec('tdem')['variables']['transmitter']
        cls.__stm_moment(transmitter, variables, stated, normalisations, placeholders)

        per_transmitter = ('number_of_turns', 'peak_current', 'area', 'base_frequency')
        for field, (block, key, values) in stated.items():
            placed = cls.__stm_per_transmitter(values, placeholders.get(field)) \
                if field in per_transmitter else cls.__stm_agreed(values)
            if placed is None:
                continue

            (transmitter if field in per_transmitter else variables)[field] = placed
            for stm in blocks.values():
                stm.get(block, {}).pop(key, None)

        found = {'mode': 'airborne', 'dimensions': dimensions, 'variables': variables}
        found.update(cls.__stm_provenance(files, blocks))

        return found, labels, receivers

    @classmethod
    def __stm_gates(cls, named, label, transmitters, path, stm):
        """One gate per window the file lists, bounded by when it opened and closed."""
        receiver = stm.get('receiver', {})
        windows = receiver.pop('window_times', None)
        counted = receiver.pop('number_of_windows', None)

        if windows is None:
            raise ValueError(f"{path} has no WindowTimes, so it does not say when its gates were")

        if counted is not None and counted != len(windows):
            raise ValueError(f"{path} says NumberOfWindows = {counted} but lists {len(windows)} "
                             "of them")

        spelled = 'gate times' if len(transmitters) == 1 else f"{label} gate times"
        return {'long_name': spelled,
                'bounds': windows,
                'centers': [0.5 * (opened + closed) for opened, closed in windows]}

    @staticmethod
    def __stm_components(blocks):
        """The components a file scales its output by, which are the coils that read it."""
        scalings = []
        for stm in blocks.values():
            forward = stm.get('forward_modelling', {})
            scalings.append({axis: forward.pop(f"{axis}_output_scaling", 0) for axis in 'xyz'})

        components = [axis for axis in 'xyz' if any(scaling[axis] for scaling in scalings)]

        return components if components else ['z']

    @staticmethod
    def __stm_waveform(times, currents):
        """The waveforms of every transmitter, on one time axis.

        ``waveform_current`` is declared over n_transmitter by waveform_time, so the
        moments cannot each bring their own vertices. A waveform is straight between
        its vertices, so interpolating onto the union of them puts back exactly what
        each file stated, and a transmitter is off outside its own waveform.

        """
        if len(times) == 1:
            return list(times[0]), [list(currents[0])]

        shared = sorted({time for stated in times for time in stated})

        return shared, [np.interp(shared, stated, current, left=0.0, right=0.0).tolist()
                        for stated, current in zip(times, currents)]

    @staticmethod
    def __stm_data_type(text, normalisation=None):
        """What the file delivers, spelled the way GSPy spells it.

        SecondaryFieldNormalisation divides the secondary field by the primary one,
        which is what makes the delivered numbers ppm whichever field was modelled to
        get there. Which flavour of ppm it was is left to the provenance.

        """
        if str(normalisation).lower() in ('ppm', 'ppmpeaktopeak'):
            return 'ppm'
        return {'db/dt': 'dBdt', 'dbdt': 'dBdt', 'b': 'B'}.get(str(text).lower(), text)

    @classmethod
    def __stm_per_transmitter(cls, values, placeholder):
        """One value per transmitter, the placeholder where a file did not say, or
        nothing if none did. GA-AEM assumes no value for a field a file leaves out."""
        if all(value is None for value in values):
            return None
        return cls._template_repeat_to([placeholder if value is None else value for value in values])

    @classmethod
    def __stm_moment(cls, transmitter, variables, stated, normalisations, placeholders):
        """Each transmitter's moment, from its loop, and whether the data were normalised by it.

        GA-AEM scales its output by turns x area x peak current and compares it with
        the data, so the data are in the units of the moment the file states: a unit
        moment means normalised, and ppm is normalised whatever the moment.

        """
        loops = zip(*(stated[field][2] for field in ('number_of_turns', 'area', 'peak_current')))
        moments = [float(np.prod(parts)) if all(isinstance(part, (int, float)) for part in parts)
                   else None for parts in loops]

        if any(moment is not None for moment in moments):
            for field in ('peak_moment', 'moment'):
                transmitter[field] = cls._template_repeat_to(
                    [placeholders[field] if moment is None else moment for moment in moments])

        normalised = [True if str(normalisation).lower() in ('ppm', 'ppmpeaktopeak')
                      else None if moment is None else moment == 1.0
                      for moment, normalisation in zip(moments, normalisations)]
        if None not in normalised and len(set(normalised)) == 1:
            variables['data_normalized'] = normalised[0]

    @classmethod
    def __stm_remoment(cls, transmitter, given):
        """The moment of the loop the yml put back, where it put one back and did not
        state the moment itself. ``data_normalized`` stays judged by the file's loop,
        the one the forward model scales by."""
        loop = ('number_of_turns', 'area', 'peak_current')
        if not any(field in given for field in loop):
            return

        values = [transmitter.get(field) for field in loop]
        values = [value.get('values') if isinstance(value, dict) else value for value in values]
        count = max(len(value) if isinstance(value, (list, tuple)) else 1 for value in values)
        parts = zip(*(list(value) if isinstance(value, (list, tuple)) else [value] * count
                      for value in values))
        moments = [float(np.prod(part)) if all(isinstance(p, (int, float)) for p in part) else None
                   for part in parts]
        if None in moments:
            return
        for field in ('peak_moment', 'moment'):
            if field not in given:
                if isinstance(transmitter.get(field), dict):
                    transmitter[field]['values'] = cls._template_repeat_to(moments)
                else:
                    transmitter[field] = cls._template_repeat_to(moments)

    @staticmethod
    def __stm_agreed(values):
        """The one value every file states, or nothing if they differ or one is silent."""
        if any(value is None for value in values) or len({repr(v) for v in values}) > 1:
            return None
        return values[0]

    @classmethod
    def __stm_provenance(cls, files, blocks):
        """The file, and everything read from it that has no field of its own.

        Keyed by where it sat in the file, so ``stm_forward_modelling_output_scaling``
        is plainly a GA-AEM modelling setting rather than a property of the system.
        Where the moments disagree, both are recorded, in the order given.

        """
        out = {'stm_file': ', '.join(os.path.basename(path) for path in files.values())}

        flattened = [Metadata(stm).flatten() for stm in blocks.values()]
        for key in unique_list_preserve([key for stm in flattened for key in stm]):
            values = [stm[key] for stm in flattened if key in stm]
            agreed = cls.__stm_agreed(values) if len(values) == len(flattened) else None
            out[f"stm_{key.replace('.', '_')}"] = agreed if agreed is not None \
                else ', '.join(str(value) for value in values)

        return out

    @classmethod
    def __stm_frequency_domain(cls, files, read, receivers):
        """What a csv table .stm says about a frequency domain system."""
        if len(read) > 1:
            raise ValueError("A frequency domain .stm holds every coil pair of a system, so it "
                             f"is read from one file, not the {len(read)} it was given")

        path, table = next(iter(files.values())), deepcopy(next(iter(read.values())))
        if table.pop('format') != 'table':
            raise ValueError("A frequency domain system is read from a csv table of coil pairs, "
                             f"but {path} is a 'System Begin' block")

        frequencies = table.pop('freq')
        transmitted = table.pop('tor', None)
        received = table.pop('ror', None)
        if transmitted is None or received is None:
            raise ValueError(f"{path} does not say which way its coils point, so its pairs "
                             "cannot be labelled")

        labels = [f"{frequency}{orientation.upper()}"
                  for frequency, orientation in zip(frequencies, transmitted)]

        variables = {'transmitter': {'orientation': transmitted},
                     'receiver': {'orientation': received},
                     'couplet': {}}

        for axis, transmitter, receiver in (('dx', 'tx', 'rx'), ('dy', 'ty', 'ry'),
                                            ('dz', 'tzoff', 'rzoff')):
            at, to = table.pop(transmitter, None), table.pop(receiver, None)
            if at is not None and to is not None:
                variables['couplet'][f"txrx_{axis}"] = [b - a for a, b in zip(at, to)]

        # Vertical dipoles fly one above the other, horizontal ones end to end.
        pairs = [{('z', 'z'): 'coplanar', ('x', 'x'): 'coaxial'}.get(pair)
                 for pair in zip(transmitted, received)]
        if all(pair is not None for pair in pairs):
            variables['couplet']['orientation'] = pairs

        # The moment as stated, sign and all: a negative one is a coil wound the other
        # way up. Whether the data it is attached to was scaled by it is not the file's
        # to say.
        if 'tmom' in table:
            variables['transmitter']['moment'] = table.pop('tmom')

        found = {'mode': 'airborne',
                 'dimensions': {'frequency': {'centers': frequencies}},
                 'variables': variables}
        found.update(cls.__stm_provenance(files, {None: table}))

        return found, labels, labels if receivers is None else receivers

    @classmethod
    def open(cls, filename, name=None, **kwargs):
        """One system, read from a metadata file.

        Parameters
        ----------
        filename : str
            The file. A system is an entry named with "system" in it, which is how a
            container picks them out of a dataset's metadata too, so a file written
            for a dataset can be opened here as well.
        name : str, optional
            Which system to build. Only needed where the file holds more than one.

        Returns
        -------
        xarray.Dataset

        Raises
        ------
        ValueError
            If the file holds no system, or holds several and none was asked for.

        Examples
        --------
        >>> System.open('Resolve_system.yml')
        >>> System.open('skytem_system.yml', name='magnetic_system')

        """
        md = Metadata.read(filename, **kwargs)
        systems = {key: value for key, value in md.items()
                   if 'system' in key and isinstance(value, dict)}

        if not systems:
            raise ValueError(f"{filename} holds no system. A system is read from an entry named "
                             "with 'system' in it, such as 'skytem_system'")

        if name is None and len(systems) > 1:
            raise ValueError(f"{filename} holds more than one system, so say which one to open: "
                             f"{', '.join(sorted(systems))}")

        name = next(iter(systems)) if name is None else name
        if name not in systems:
            raise ValueError(f"{filename} holds no system called '{name}', only "
                             f"{', '.join(sorted(systems))}")

        return cls.from_dict(name=name, **systems[name])

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

        self.__check_moment()

        # Cannot have literal Booleans in the attributes of a netcdf...
        # Convert to strings...
        for k, v in kwargs.items():
            if isinstance(v, bool):
                kwargs[k] = "True" if v else "False"

        self._obj.attrs = self._obj.attrs | kwargs

        return self._obj

    def __check_moment(self):
        """A moment stated beside its loop has to be turns x area x peak current, the
        product a forward model scales by. One not yet known is not checked."""
        numbers = {}
        for field in ('number_of_turns', 'area', 'peak_current', 'peak_moment', 'moment'):
            variable = self._obj.get(f"transmitter_{field}")
            if variable is not None and variable.dtype.kind in "iuf":
                numbers[field] = variable.values

        if not {'number_of_turns', 'area', 'peak_current'} <= set(numbers):
            return

        product = numbers['number_of_turns'] * numbers['area'] * numbers['peak_current']
        for field in ('peak_moment', 'moment'):
            if field in numbers and not np.allclose(numbers[field], product):
                raise ValueError(f"transmitter {field} {numbers[field]} is not turns x area x peak current, "
                                 f"{product}")

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
            values = dict(values) if isinstance(values, dict) else dict(values=values)
            # One value, next to its key or nested under it, is every entry's.
            if 'values' in values and 'dimensions' not in values and np.ndim(values['values']) == 0:
                values['values'] = np.full(n_entries, fill_value=values['values'])
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
