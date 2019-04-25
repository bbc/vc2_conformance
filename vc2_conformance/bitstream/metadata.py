"""
Metadata about the VC-2 bitstream seriallisation/deseriallisation process.
"""

from vc2_conformance.bitstream import vc2
from vc2_conformance.bitstream.vc2_fixeddicts import HQSlice, LDSlice


__all__ = [
    "pseudocode_function_to_fixeddicts",
    "pseudocode_function_to_fixeddicts_recursive",
]


pseudocode_function_to_fixeddicts = {}
"""
For the subset of pseudocode functions in the VC-2 spec dedicated to
serialisation/deseriallisation, gives the corresponding fixeddict type in
:py:mod:`vc2_fixeddicts`.

A dictionary of the shape ``{function_name: [type, ...], ...}``.
"""

# Populate pseudocode_function_to_fixeddicts
for name in vc2.__all__:
    function = getattr(vc2, name)
    if hasattr(function, "context_type"):
        pseudocode_function_to_fixeddicts[name] = [function.context_type]
    else:
        pseudocode_function_to_fixeddicts[name] = []

# Special case: 'slice' may have one of two types and this is not indicated by
# a @context_type decorator
assert "slice" in pseudocode_function_to_fixeddicts
assert pseudocode_function_to_fixeddicts["slice"] == []
pseudocode_function_to_fixeddicts["slice"].append(HQSlice)
pseudocode_function_to_fixeddicts["slice"].append(LDSlice)

# Special case: 'slice_band' and 'color_diff_slice_band' both only serve to
# update an existing slice and so don't have a type. Remove these from the
# listing to avoid being misleading
assert pseudocode_function_to_fixeddicts.pop("slice_band") == []
assert pseudocode_function_to_fixeddicts.pop("color_diff_slice_band") == []


pseudocode_function_to_fixeddicts_recursive = {}
"""
Like :py:data:`pseudocode_function_to_fixeddicts` but each entry also
recursively includes the fixeddict types of all contained entries.
"""

# Populate pseudocode_function_to_fixeddicts_recursive
def iter_fixeddict_types(fixeddict):
    yield fixeddict
    for entry in fixeddict.entry_objs.values():
        if entry.type is not None:
            for subtype in iter_fixeddict_types(entry.type):
                yield subtype

for name, base_types in pseudocode_function_to_fixeddicts.items():
    types = []
    for base_type in base_types:
        types.extend(iter_fixeddict_types(base_type))
    pseudocode_function_to_fixeddicts_recursive[name] = types
