"""
Internal minor utility functions; mainly relating to string formatting.
"""


def indent(text, prefix="  "):
    """Indent the string 'text' with the prefix string 'prefix'."""
    return "{}{}".format(
        prefix,
        ("\n{}".format(prefix)).join(text.split("\n")),
    )

def concat_strings(strings):
    """
    Sensibly concatenate a series of strings, with the following 'smart'
    behaviours:
    
    * If any string contains a newline, concatenate with newlines, not spaces
    * If any string is empty, omit it entirely
    """
    if any("\n" in s for s in strings):
        seperator = "\n"
    else:
        seperator = " "
    
    return seperator.join(filter(None, strings))
