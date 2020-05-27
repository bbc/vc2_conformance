"""
Sphinx extension for documenting fixeddict types. Use in place of ``..
py:class::`` and ``..  autoclass::`` for slightly neater presentation.
Cross-reference using ``:py:class:`` as usual, however.

Usage::

    Hand-specified (NB, using the form output by numpydoc, not the sphinx
    native form, for consistency with numpydoc documented fixeddicts):

    .. py:fixeddict:: Foo

        What would you like to know?

        :Parameters:

            **a**
                A thing.

            **b**
                Another thing.

            **c** : *str*

                A string thing

    Auto-generated:

    .. autofixeddict:: path.to.Foo

"""

from docutils import nodes

from sphinx.domains.python import PyClasslike
from sphinx.ext.autodoc import ClassDocumenter


class FixeddictDirective(PyClasslike):
    """
    Implements the ``.. py:fixeddict::`` directive.
    """

    def get_index_text(self, modname, name_cls):
        return "{} (fixeddict in {})".format(name_cls[0], modname)

    def handle_signature(self, sig, signode):
        # Strip arguments from signature
        sig = sig.partition("(")[0]
        return super().handle_signature(sig, signode)

    def transform_content(self, content_node):
        # Rename ':Parameters:' to ':Keys:' (as added by numpydoc)
        for field_name in content_node.traverse(
            lambda node: isinstance(node, nodes.field_name)
        ):
            if field_name.astext() == "Parameters":
                field_name.clear()
                field_name += nodes.Text("Keys")


class FixeddictDocumenter(ClassDocumenter):
    """
    Specialized ClassDocumenter subclass for fixeddicts. Causes autodoc to
    generate a ``..  autofixeddict::`` directive (and use ``.. py:fixeddict::``
    for documenting member fixeddicts!).
    """

    objtype = "fixeddict"
    member_order = 10

    # needs a higher priority than ClassDocumenter
    priority = 10

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return (
            isinstance(member, type)
            and issubclass(member, dict)
            and hasattr(member, "entry_objs")
        )


def setup(app):
    app.add_directive("py:fixeddict", FixeddictDirective)
    app.add_autodocumenter(FixeddictDocumenter)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
