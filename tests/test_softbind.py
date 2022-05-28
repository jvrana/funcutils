#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
#  Copyright (c) Just-Biotherapeutics, Seattle, WA 2022. All rights reserved.
import inspect

from funcutils.softbind import soft_bind


def test_soft_bind():
    def foo(a: int, *, c: int = 4, d: int = 5):
        ...

    s = inspect.signature(foo)

    args = (1, 2, 3)
    kwargs = {"c": 5}

    ret = soft_bind(s, args, kwargs)

    print(ret.get_params(bound=True))
    assert len(ret.get_params(bound=True)) == 2
    assert len(ret.get_params(bound=False)) == 1
    assert len(ret.get_values(bound=True)) == 2
    assert len(ret.get_values(bound=False)) == 2

    param0 = ret.get_params(bound=True)[0]
    value0 = ret.get_values(bound=True)[0]
    param0.value is value0
    value0.param is param0
    print(param0)
    print(value0)

    ret.bound_signature()
    ret.unbound_signature()

    print(ret.get_args(bound=False))
    print(ret.get_args(bound=True))
    print(ret.get_kwargs(bound=False))
    print(ret.get_kwargs(bound=True))
