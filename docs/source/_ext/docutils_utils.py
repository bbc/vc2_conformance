from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.util.nodes import nested_parse_with_titles


def make_row(entries):
    """
    Make a row containing the supplied set of cell values (docutils nodes). To
    make a wide cell, enclose the docutils node in a (node, width) tuple.
    """
    row = nodes.row()

    for node_width in entries:
        if isinstance(node_width, tuple):
            node, width = node_width
        else:
            node = node_width
            width = 1

        if width == 1:
            entry = nodes.entry("", node)
        else:
            entry = nodes.entry("", node, morecols=width - 1)

        row += entry

    return row


def make_text(text):
    return nodes.paragraph(text=text)


def make_literal(text):
    return nodes.literal(text=text)


def make_from_rst(state, rst):
    inline = nodes.inline()
    nested_parse_with_titles(state, ViewList(rst.splitlines()), inline)

    # Remove wrapping inline if possible
    if len(inline.children) == 1:
        return inline.children[0]
    else:
        return inline


def make_table(headings, values, colwidths=None):
    """
    Make a table with the specified headings and values (given as docutils
    nodes, or (node, width) tuples). If colwidths is None, uses '1' for all
    columns, otherwise must be a list of integer weights.
    """
    table = nodes.table()

    num_cols = 0
    for heading in headings:
        if isinstance(heading, tuple):
            _, width = heading
            num_cols += width
        else:
            num_cols += 1

    tgroup = nodes.tgroup(cols=len(headings))
    table += tgroup

    if colwidths is None:
        for i in range(num_cols):
            tgroup += nodes.colspec(colwidth=1)
    else:
        assert len(colwidths) == num_cols
        for colwidth in colwidths:
            tgroup += nodes.colspec(colwidth=colwidth)

    thead = nodes.thead("", make_row(headings))
    tgroup += thead

    tbody = nodes.tbody()
    tgroup += tbody

    for row_nodes in values:
        tbody += make_row(row_nodes)

    return table
