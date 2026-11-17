"""Plot labels: GSPy names axes by standard_name, xarray by long_name.

Every GS variable carries a CF standard_name, and its long_name is prose that
wraps to several lines on an axis. xarray's plot layer prefers long_name when
both are set, with no option to reorder; the plotters import that one helper
under their own names, so switching the order means rebinding those names.
If a future xarray moves it, the patch quietly does nothing and the labels
revert to xarray's own behaviour.
"""
import textwrap

try:
    from xarray.plot.utils import _get_units_from_attrs
    _PATCHABLE = True
except ImportError:
    _PATCHABLE = False


def label_from_attrs(da, extra=""):
    """Informative label from CF metadata, standard_name first.

    Falls back to long_name, then the variable name, matching xarray where a
    standard_name is absent or still the 'not_defined' placeholder.
    """
    if da is None:
        return ""

    name = da.attrs.get("standard_name") or ""
    if not name or name == "not_defined":
        name = da.attrs.get("long_name") or (da.name if da.name is not None else "")

    units = _get_units_from_attrs(da)

    if name.startswith("$") and (name.count("$") % 2 == 0):
        return "$\n$".join(textwrap.wrap(name + extra + units, 60, break_long_words=False))
    return "\n".join(textwrap.wrap(name + extra + units, 30))


def patch_xarray_labels():
    """Point xarray's plotting label helper at the standard_name-first one."""
    if not _PATCHABLE:
        return
    for module_name in ("xarray.plot.utils", "xarray.plot.dataarray_plot",
                        "xarray.plot.facetgrid"):
        try:
            module = __import__(module_name, fromlist=["label_from_attrs"])
        except ImportError:
            continue
        module.label_from_attrs = label_from_attrs
