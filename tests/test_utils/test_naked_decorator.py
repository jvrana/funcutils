#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from jdv_funcutils.utils.decorators import naked_decorator


def test_naked_decorator():
    @naked_decorator
    def mydecoratator(name="default"):
        def rename(fn):
            fn.__name__ = name
            return fn

        return rename

    @mydecoratator
    def foo():
        ...

    @mydecoratator()
    def bar():
        ...

    @mydecoratator(name="other_name")
    def baz():
        ...

    assert foo.__name__ == "default"
    assert bar.__name__ == "default"
    assert baz.__name__ == "other_name"
