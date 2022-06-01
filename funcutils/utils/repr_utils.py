#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import inspect
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from funcutils.utils import Null


def resolve_attr(obj, name, default: Any = Null):
    if name is not None and hasattr(obj, name):
        value = getattr(obj, name)
    else:
        value = default
    if value is Null:
        value = default
    if inspect.ismethod(value):
        value = value(obj)
    return value


class ReprMixin:
    __repr_name__: Optional[Union[str, Tuple[str, Callable]]] = Null
    __repr_attrs__: Optional[List[Union[str, Tuple[str, Callable]]]] = None

    def __repr__(self):
        repr_attrs = self.__repr_attrs__
        if repr_attrs is None:
            repr_attrs = self.__slots__
        clsname = resolve_attr(self, "__repr_name__", self.__class__.__name__)
        attr_tokens = []
        for x in repr_attrs:
            default = Null
            if isinstance(x, tuple):
                x, default = x
            v = resolve_attr(self, x, default=default)
            if v is not Null:
                attr_tokens.append(f"{x}={v}")
        attr_str = " ".join(attr_tokens)
        return f"<{clsname}({attr_str})>"

    def __str__(self):
        return self.__repr__()
