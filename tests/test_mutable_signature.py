#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import inspect
from copy import deepcopy

import pytest

from funcutils import MutableSignature
from funcutils import SignatureException
from funcutils.signature_extended import BoundSignature


class TestSignatureExtended:
    @pytest.fixture()
    def foo(self):
        def foo(a: int, b: int):
            ...

        return foo

    @pytest.fixture()
    def s(self, foo):
        s = MutableSignature(foo)
        return s

    def test_str(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert (
            s.__str__() == "<MutableSignature(a: int, b: str, c: float = 4.0) -> float>"
        )

    def test_repr(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert (
            s.__repr__()
            == "<MutableSignature(a: int, b: str, c: float = 4.0) -> float>"
        )

    def test_get_param(self, s):
        assert s.get_param("b").name == "b"

        with pytest.raises(SignatureException, match="Could not find parameter 'c'"):
            s.get_param("c")

    def test_param_list(self, s, foo):
        assert tuple(s.to_signature().parameters.values()) == tuple(
            inspect.signature(foo).parameters.values()
        )

    def test_param_dict(self, s, foo):
        assert s.get_signature_parameters() == tuple(
            inspect.signature(foo).parameters.values()
        )

    def test_del(self, s, foo):
        del s["a"]
        assert len(s) == 1
        assert (
            s.get_signature_parameters()
            == tuple(inspect.signature(foo).parameters.values())[1:]
        )

    def test_append(self, s, foo):
        s.append(
            inspect.Parameter(name="c", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        assert len(s) == 3
        assert list(s.to_signature().parameters.values())[0].name == "a"
        assert list(s.to_signature().parameters.values())[1].name == "b"
        assert list(s.to_signature().parameters.values())[2].name == "c"

    def test_insert(self, s, foo):
        s.insert(
            1, inspect.Parameter(name="c", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        assert len(s) == 3
        assert list(s.to_signature().parameters.values())[0].name == "a"
        assert list(s.to_signature().parameters.values())[1].name == "c"
        assert list(s.to_signature().parameters.values())[2].name == "b"

    def test_invalid_signature(self, s, foo):
        s.insert(1, inspect.Parameter(name="c", kind=inspect.Parameter.KEYWORD_ONLY))
        with pytest.raises(ValueError):
            s.to_signature()

    def test_soft_bind(self):
        def foo(a: int, *, c: int = 4, d: int = 5):
            ...

        s = MutableSignature(foo)

        args = (1, 2, 3)
        kwargs = {"c": 5}

        ret = s.soft_bind(args, kwargs)

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

    def test_permute_by_name(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        s.permute("b", "a", "c")
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[1], params[0], params[2]]
        assert s.get_signature_parameters() == tuple(expected)

    def test_permute_by_pos(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        s.permute(1, 0, 2)
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[1], params[0], params[2]]
        assert s.get_signature_parameters() == tuple(expected)

    def test_permute_by_pos_error(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        with pytest.raises(SignatureException):
            s.permute(0, "a", 2)

    def test_permute_by_name_kwarg(self):
        def foo(a: int, b: int, c: int = 0):
            ...

        s = MutableSignature(foo)
        s.permute("a", "c", 1)
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[0], params[2], params[1]]
        assert s.get_signature_parameters() == tuple(expected)


class TestBoundSignature:
    def test_init_with_function(self):
        def foo(a: int, b: int, c: int = 0):
            ...

        BoundSignature(foo)

    def test_init_with_mutable_signature(self):
        def foo(a: int, b: int, c: int = 0):
            ...

        BoundSignature(MutableSignature(foo))

    def test_init_with_signature(self):
        def foo(a: int, b: int, c: int = 0):
            ...

        BoundSignature(inspect.signature(foo))

    def test_bind(self):
        def fn1(a: int, b: int, c: int):
            ...

        s1 = MutableSignature(fn1)

        s2 = deepcopy(s1)
        s2.permute(1, 2, 0)

        b1 = s1.bind()
        b2 = s2.bind(1, 2, 3)
        print()
        for pv in b2.get_bound():
            print(f"Setting {pv.parameter.name} to {pv.value}")
            b1.get(pv.parameter.name).value = pv.value
        assert b2.args == (1, 2, 3)
        assert b1.args == (3, 1, 2)

    def test_invalid_bind(self):
        def fn1(a: int, b: int, c: int = 0):
            ...

        s1 = MutableSignature(fn1)

        s2 = deepcopy(s1)
        s2.permute(1, 2, 0)
        b2 = BoundSignature(s2)

        # since we permuted the signature
        # arguments (b=1, c=2, c=3) is invalid
        with pytest.raises(SignatureException):
            b2.bind(1, 2, c=3)


class TestTransform:
    def test_permute_and_transform(self):
        def fn1(a: int, b: int, c: int):
            return (a, b, c)

        s1 = MutableSignature(fn1)
        s1.permute(2, 1, 0)

        fn2 = s1.transform(fn1)

        assert fn1(1, 2, 3) == (1, 2, 3)
        assert fn2(1, 2, 3) == (3, 2, 1)

    def test_permute_and_transform_signature(self):
        def fn1(a: int, b: int, c: int):
            return (a, b, c)

        s1 = MutableSignature(fn1)
        s1.permute(2, 1, 0)

        fn2 = s1.transform(fn1)

        assert fn1(1, 2, 3) == (1, 2, 3)
        assert fn2(1, 2, 3) == (3, 2, 1)

        print(fn2)
        assert fn2.__name__ == "fn1"
        print(inspect.signature(fn2))
        print(fn2.__doc__)
        assert str(inspect.signature(fn2)) == "(c: int, b: int, a: int)"
        assert (
            fn2.__doc__
            == "Transformed function\nfn1(c: int, b: int, a: int) ==> fn1(a: int, b: int, c: int)"
        )
