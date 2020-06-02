"""
Special-purpose sphinx extension for auto-documenting the bitstream
serialisation fixeddicts in :py:mod:`vc2_conformance.bitstream.vc2_fixeddicts`.

This extension is a bit grotty but provides the following directives (which are
expected to be used once)::

    To insert a table giving a hierarchical summary of all of the fixeddicts:

    .. autobitstreamfixeddictstable::

    To automatically insert documentation for all bitstream serialisation
    fixeddicts use the following:

    .. autobitstreamfixeddicts::

Features of the above:

* The table shows the hierarchy of how fixeddicts fit together in a bitstream.
  Dicts may be repeated if they can appear in several places.
* The table shows which pseudocode function is associated with each fixeddict
* The order of the individual fixeddict documentation mirrors the table
* The fixeddict docstrings are augmented with their autofill values from
  :py:data:`vc2_conformance.bitstream.vc2_autofill.vc2_default_values_with_auto`.
* All fixeddicts are documented within the :py:mod:`vc2_conformance.bitstream`
  module namespace (rather than
  :py:mod:`vc2_conformance.bitstream.vc2_fixeddicts` module)
"""

from copy import deepcopy

from docutils import nodes

from sphinx.util.docutils import SphinxDirective

from docutils_utils import (
    make_text,
    make_literal,
    make_from_rst,
    make_table,
)

from fixeddict import FixeddictDirective, FixeddictDocumenter

from vc2_conformance.bitstream import (
    vc2_fixeddicts,
    vc2_fixeddict_nesting,
    vc2_default_values_with_auto,
    fixeddict_to_pseudocode_function,
)


def make_type_matcher(class_or_tuple):
    def match(value):
        return isinstance(value, class_or_tuple)

    return match


class BitstreamFixeddictDirective(FixeddictDirective):
    """
    Intended for internal use only.  Like ``.. py:fixeddict::`` except its
    autofill key values will be looked up in
    :py:data:`vc2_conformance.bitstream.vc2_autofill.vc2_default_values_with_auto`
    and the 'keys' list documentation augmented accordingly.
    """

    def get_signature_prefix(self, sig):
        return "fixeddict "

    def transform_content(self, content_node):
        """
        Appends autofill values to the type information of each key.
        """
        super().transform_content(content_node)

        fixeddict_type = getattr(vc2_fixeddicts, self.names[0][0], None)
        autofill_values = vc2_default_values_with_auto.get(fixeddict_type, {})

        keys_list = content_node.next_node(
            lambda node: (
                isinstance(node, nodes.field_name) and node.astext() == "Keys"
            )
        ).parent

        for entry_node in keys_list.traverse(
            make_type_matcher(nodes.definition_list_item)
        ):
            key = entry_node.next_node(make_type_matcher(nodes.term)).astext()

            if key in autofill_values:
                autofill_value = autofill_values[key]
                autofill_message = nodes.Text(
                    "(autofilled with {!r})".format(autofill_value)
                )

                classifier_node = entry_node.next_node(
                    make_type_matcher(nodes.classifier)
                )
                if classifier_node is None:
                    classifier_node = nodes.classifier()
                    classifier_node += autofill_message
                    entry_node.insert(1, classifier_node)
                else:
                    classifier_node += nodes.Text(" ")
                    classifier_node += autofill_message


class BitstreamFixeddictDocumenter(FixeddictDocumenter):
    """
    Makes autodoc create a ``.. autobitstreamfixeddict::`` directive.
    """

    objtype = "bitstreamfixeddict"

    # needs a higher priority than FixeddictDocumenter
    priority = 20

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return (
            isinstance(member, type)
            # Is fixeddict
            and issubclass(member, dict)
            and hasattr(member, "entry_objs")
            # Is bitstream fixeddict
            and member.__module__ == "vc2_conformance.bitstream.vc2_fixeddicts"
        )


def find_roots(parent_child):
    """
    Given a dictionary of {parent: [child, ...], ...} relationships, yield
    'parent' values which are not a child of any other node.
    """
    child_parent = {}
    for parent, children in parent_child.items():
        for child in children:
            child_parent[child] = parent

    for node in parent_child:
        if node not in child_parent:
            yield node


def map_tree(parent_child, root, function):
    """
    Iterate over a tree defined by a {parent: [child, ...], ...} dict, starting
    at the specified root. For each node, calls function with two arguments:
    the node and a list of mapped children. The function should return the
    mapped value.
    """
    mapped_children = [
        map_tree(parent_child, child, function) for child in parent_child.get(root, [])
    ]
    return function(root, mapped_children)


def fixeddict_nesting_to_flat_tree(nesting):
    """
    {fixeddict: [child_fixeddict, ...], ...} -> [(depth, fixeddict), ...]
    """
    nesting = deepcopy(nesting)
    # Make 'None' the new root...
    for root in list(find_roots(nesting)):
        nesting.setdefault(None, []).append(root)

    # [(depth, fixeddict), ...]
    flat_tree = map_tree(
        nesting,
        None,
        lambda node, children: ([] if node is None else [(-1, node)])
        + [
            (depth + 1, child_node) for entry in children for depth, child_node in entry
        ],
    )

    return flat_tree


class AutoBitstreamFixeddictsTable(SphinxDirective):
    """
    Defines the ``.. autobitstreamfixeddictstable::`` directive which creates a
    table enumerating the hierarchy of fixeddicts, as defined by
    :py:data:`vc2_conformance.bitstream.vc2_fixeddicts.vc2_fixeddict_nesting`.
    Also shows the pseudocode function associated with each fixeddict type as
    defined by
    :py:data:`vc2_conformance.bitstream.metadata.fixeddict_to_pseudocode_function`.
    """

    required_arguments = 0

    def run(self):
        flat_tree = fixeddict_nesting_to_flat_tree(vc2_fixeddict_nesting)

        headings = [
            make_text("Type"),
            make_text("Pseudocode function"),
        ]

        # Generate rows
        values = [
            [
                # Type column
                make_from_rst(
                    self.state,
                    "{}:py:class:`~vc2_conformance.bitstream.{}`".format(
                        # Indent with non-breaking spaces
                        b"\xA0\x00".decode("utf16") * fixeddict_depth * 4,
                        fixeddict_type.__name__,
                    ),
                ),
                # Pseudocode column
                (
                    make_literal(fixeddict_to_pseudocode_function[fixeddict_type])
                    if fixeddict_type in fixeddict_to_pseudocode_function
                    else make_text("")
                ),
            ]
            for fixeddict_depth, fixeddict_type in flat_tree
        ]

        table = make_table(headings, values)

        return [table]


class AutoBitstreamFixeddicts(SphinxDirective):
    """
    Implements the ``.. autobitstreamfixeddicts::`` directive.

    Auto-generate a series of ``.. autobitstreamfixeddict::`` directives, one
    for each fixeddict defined in
    :py:mod:`vc2_conformance.bitstream.vc2_fixeddicts`.
    """

    def run(self):
        # Add fixeddicts in hierarchical order (without duplicates)
        flat_tree = fixeddict_nesting_to_flat_tree(vc2_fixeddict_nesting)
        fixeddicts = []
        for _, fixeddict in flat_tree:
            if fixeddict not in fixeddicts:
                fixeddicts.append(fixeddict)

        out = make_from_rst(
            self.state,
            "\n\n".join(
                ".. autobitstreamfixeddict:: vc2_conformance.bitstream.{}".format(
                    fixeddict.__name__,
                )
                for fixeddict in fixeddicts
            ),
        )

        return [out]


def setup(app):
    app.add_directive("py:bitstreamfixeddict", BitstreamFixeddictDirective)
    app.add_autodocumenter(BitstreamFixeddictDocumenter)

    app.add_directive("autobitstreamfixeddictstable", AutoBitstreamFixeddictsTable)
    app.add_directive("autobitstreamfixeddicts", AutoBitstreamFixeddicts)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
