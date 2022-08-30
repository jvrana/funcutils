#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import functools
from typing import Callable


def naked_decorator(fn: Callable[[Callable], Callable]) -> Callable:
    """Dispatches a normal decorator into a naked decorator. For example:

    .. code-block:: python

        @naked_decorator
        def my_decorator(a: int)
            def inner_fn(fn):
                print(a)
                return fn
            return inner_fn

        # naked decorator usage
        @my_decorator
        def foo():
            ...

        # normal decorator usage
        @my_decorator(a=5)
        def bar():
            ...

    :param fn: The decoratory function
    :return:
    """

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if not kwargs and len(args) == 1 and callable(args[0]):
            return fn()(args[0])
        else:
            return fn(*args, **kwargs)

    return wrapped
