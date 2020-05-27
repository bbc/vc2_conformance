"""
Sphinx extension which produces a table of :py:class:`enum.Enum` values and
names.

Usage example::

    .. enum-value-table:: vc2_data_tables.BaseVideoFormats
        :value-heading: Color Primaries Index
        :name-heading: Alias

The ``:value-heading:`` and ``:name-heading:`` options default to "Value" and
"Name" if not specified.
"""

from importlib import import_module

from docutils.parsers.rst import Directive

from docutils_utils import (
    make_text,
    make_literal,
    make_table,
)


class EnumValueTable(Directive):

    required_arguments = 1  # enum name

    option_spec = {
        "value-heading": str,
        "name-heading": str,
    }

    def run(self):
        module_name, _, enum_name = self.arguments[0].rpartition(".")

        enum_type = getattr(import_module(module_name), enum_name)

        value_heading = self.options.get("value-heading", "Value")
        name_heading = self.options.get("name-heading", "Name")
        rows = [(str(value.value), value.name) for value in enum_type]

        value_column_width = max(map(len, [value_heading] + [v for v, _ in rows]))
        name_column_width = max(map(len, [name_heading] + [n for _, n in rows]))

        table = make_table(
            (make_text(value_heading), make_text(name_heading)),
            [(make_text(value), make_literal(name)) for value, name in rows],
            (value_column_width, name_column_width),
        )

        return [table]


def setup(app):
    app.add_directive("enum-value-table", EnumValueTable)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
