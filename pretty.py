"""
Pretty. Base class for a simple pretty, properly indented representation of a class.

Example:
    >>> class K(Pretty):
    ...   def __init__(self):
    ...      self.a = 5
    ...      self.b = 6
    ...
    >>> K()
    K(
       a=5,
       b=6
    )
"""
from typing import Set


class Pretty:
    """
    Base class for a pretty, properly indented __repr__ method.
    """

    __current_indent = 0
    __hidden__: Set[str] = set()

    def __repr__(self):
        indent = self.__current_indent * 3 * ' '
        if not self.__dict__:
            return '%s()' % type(self).__name__
        Pretty.__current_indent += 1
        inner = ',\n'.join(
            '   %s%s=%r' % (indent, k, v)
            if k not in self.__hidden__
            else '   %s%s=...' % (indent, k)
            for k, v in self.__dict__.items()
        )
        pattern = '%s(\n%s\n%s)'
        result = pattern % (
            type(self).__name__,
            inner,
            indent,
        )
        Pretty.__current_indent -= 1
        return result
