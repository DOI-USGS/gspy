"""Reading GA-AEM .stm system files.

Two formats answer to the extension. A time domain system is a nest of
``Name Begin`` ... ``Name End`` blocks holding ``Key = value`` pairs and tables
of unkeyed numbers. A frequency domain system is a csv table, a header row of
column names then a row per coil pair.

Nothing here knows what GSPy calls any of this. A file comes back as it was
written, with its keys snake cased and its numbers read as numbers, and
:meth:`gspy.System.metadata_from_stm` does the interpreting.
"""
import re

# Split CamelCase where a word ends, either at a lowercase to uppercase step or
# at the tail of a run of capitals, so XOutputScaling gives x_output_scaling.
_WORD_BREAK = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')

_BEGIN = ' begin'
_END = ' end'


def read_stm(filename, **kwargs):
    """Read a GA-AEM .stm system file.

    Parameters
    ----------
    filename : str
        Path to the file.

    Returns
    -------
    dict
        The file as written, under snake cased keys, with a ``format`` entry of
        "block" or "table" saying which of the two it was. A block file comes
        back unwrapped, since the whole of it is one ``System`` block.

    Raises
    ------
    ValueError
        If the file is neither format, or if a block is left open.

    """
    with open(filename) as f:
        lines = f.readlines()

    for line in lines:
        text = _strip(line)
        if text == '':
            continue

        if text.lower().startswith('system' + _BEGIN):
            return {'format': 'block'} | _read_blocks(lines, filename)

        if text.lower().split(',')[0].strip() == 'freq':
            return {'format': 'table'} | _read_table(lines, filename)

        break

    raise ValueError(f"{filename} is not a GA-AEM .stm file: expected either a 'System Begin' "
                     "block or a header row of coil pair columns beginning with 'freq'")


def _strip(line):
    """A line without its comment or its whitespace."""
    return line.split('//')[0].strip()


def _read_blocks(lines, filename):
    """The contents of the outermost block, which is the whole file."""
    stack = []

    for line in lines:
        text = _strip(line)
        if text == '':
            continue

        lowered = text.lower()

        if lowered.endswith(_BEGIN):
            stack.append([text[:-len(_BEGIN)].strip(), {}, []])

        elif lowered.endswith(_END):
            name = text[:-len(_END)].strip()
            if not stack or stack[-1][0].lower() != name.lower():
                raise ValueError(f"'{name} End' in {filename} closes a block that is not open")

            opened, block, rows = stack.pop()
            if rows:
                block = rows if not block else block | {'values': rows}

            if not stack:
                return block
            stack[-1][1][_key(opened)] = block

        elif not stack:
            raise ValueError(f"'{text}' in {filename} sits outside any block")

        elif '=' in text:
            key, _, value = text.partition('=')
            stack[-1][1][_key(key)] = _value(value)

        else:
            row = _value(text.replace(',', ' '))
            stack[-1][2].append(row if isinstance(row, list) else [row])

    raise ValueError(f"'{stack[0][0]} Begin' in {filename} is never closed")


def _read_table(lines, filename):
    """A column per name in the header row."""
    rows = [t for t in (_strip(line) for line in lines) if t != '']
    names = [_key(name) for name in rows[0].split(',')]

    columns = {name: [] for name in names}
    for row in rows[1:]:
        entries = [entry.strip() for entry in row.split(',')]
        if len(entries) != len(names):
            raise ValueError(f"Row '{row}' of {filename} has {len(entries)} entries "
                             f"where its header names {len(names)} columns")

        for name, entry in zip(names, entries):
            number = _number(entry)
            columns[name].append(entry.lower() if number is None else number)

    return columns


def _key(name):
    """CamelCase to snake_case.

    GA-AEM spells the waveform both WaveForm and Waveform, which would come out
    as two different keys.

    """
    return _WORD_BREAK.sub('_', name.strip().replace('WaveForm', 'Waveform')).lower()


def _value(text):
    """The right hand side of a pair: a number, several of them, or a string."""
    numbers = [_number(token) for token in text.split()]

    if numbers and all(number is not None for number in numbers):
        return numbers[0] if len(numbers) == 1 else numbers

    return text.strip()


def _number(token):
    """A token as an int or a float, or None if it is neither."""
    for cast in (int, float):
        try:
            return cast(token)
        except ValueError:
            pass
    return None
