#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import inspect
from copy import deepcopy
from typing import Any
from typing import NamedTuple
from typing import Tuple

import pytest

from funcutils import MutableSignature
from funcutils.signature.mutable_signature import BoundSignature
from funcutils.signature.mutable_signature import MutableParameterTuple
from funcutils.signature.mutable_signature import named_tuple_type_constructor
from funcutils.signature.mutable_signature import SignatureException
from funcutils.signature.mutable_signature import SignatureMissingParameterException
from funcutils.signature.mutable_signature import tuple_type_constructor


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

    def test_getitem(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert s[0].name == "a"
        assert s["a"].name == "a"
        assert s[1].name == "b"
        assert s["b"].name == "b"
        assert s[2].name == "c"
        assert s["c"].name == "c"
        with pytest.raises(SignatureMissingParameterException):
            s[3]

    def test_getitem_with_mutable_param(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert s[s[0]] == s[0]

    def test_iter(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert [p.name for p in s] == ["a", "b", "c"]

    def test_contains(self):
        def bar(a: int, b: str, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert 0 in s
        assert 1 in s
        assert 2 in s
        assert 3 not in s
        assert "a" in s
        assert "b" in s
        assert "c" in s
        assert "d" not in s

    def test_contains_kwonly(self):
        def bar(a: int, b: str, *, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert 0 in s
        assert 1 in s
        assert 2 not in s
        assert 3 not in s
        assert "a" in s
        assert "b" in s
        assert "c" in s
        assert "d" not in s

    def test_contains_posonly(self):
        def bar(a: int, b: str, /, c: float = 4.0) -> float:
            ...

        s = MutableSignature(bar)
        assert 0 in s
        assert 1 in s
        assert 2 in s
        assert 3 not in s
        assert "a" not in s
        assert "b" not in s
        assert "c" in s
        assert "d" not in s

    def test_get_param(self, s):
        assert s.get_param("b").name == "b"

        with pytest.raises(
            SignatureMissingParameterException, match="Could not find parameter 'c'"
        ):
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
        s.add(inspect.Parameter(name="c", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD))
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

    def test_soft_bind(self):
        def foo(a: int, *, c: int = 4, d: int = 5):
            ...

        s = MutableSignature(foo)

        args = (1, 2, 3)
        kwargs = {"c": 5}

        ret = s.bind(*args, **kwargs)

        print(ret.bound)
        assert len(ret.bound) == 2
        print(ret.unbound_parameters)
        assert len(ret.unbound_parameters) == 1

        print(ret.get_args(bound=False))
        print(ret.get_args(bound=True))
        print(ret.get_kwargs(bound=False))
        print(ret.get_kwargs(bound=True))

        ret.bound_signature()
        ret.unbound_signature()

    def test_permute_by_name(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        s.reorder("b", "a", "c")
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[1], params[0], params[2]]
        assert s.get_signature_parameters() == tuple(expected)

    def test_permute_by_pos(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        s.reorder(1, 0, 2)
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[1], params[0], params[2]]
        assert s.get_signature_parameters() == tuple(expected)

    def test_permute_by_pos_error(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        with pytest.raises(SignatureException):
            s.reorder(0, "a", 2)

    def test_permute_by_name_kwarg(self):
        def foo(a: int, b: int, c: int):
            ...

        s = MutableSignature(foo)
        s.reorder("a", "c", 1)
        params = list(inspect.signature(foo).parameters.values())
        expected = [params[0], params[2], params[1]]
        assert s.get_signature_parameters() == tuple(expected)


class TestBoundSignature:
    def test_new_signature(self):
        x = MutableSignature()
        print(x.params)
        print(x.params)
        x.add("a", int)
        x.add("d", float, kind=x.KEYWORD_ONLY, default=5.0)
        x.add("b", int)
        x.add("c", float, kind=x.POSITIONAL_ONLY)
        print(x.to_signature())
        assert (
            str(x.to_signature()) == "(c: float, /, a: int, b: int, *, d: float = 5.0)"
        )

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
        s2.reorder(1, 2, 0)

        b1 = s1.bind()
        b2 = s2.bind(1, 2, 3)
        print()
        for pv in b2.bound:
            b1.get(pv.parameter.name).value = pv.value
        assert b2.args == (1, 2, 3)
        assert b1.args == (3, 1, 2)

    def test_invalid_bind(self):
        def fn1(a: int, b: int, c: int = 0):
            ...

        s1 = MutableSignature(fn1)

        s2 = deepcopy(s1)
        s2.reorder(1, 2, 0)
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
        s1.reorder(2, 1, 0)

        fn2 = s1.transform(fn1)

        assert fn1(1, 2, 3) == (1, 2, 3)
        assert fn2(1, 2, 3) == (3, 2, 1)

    def test_permute_and_transform_signature(self):
        def fn1(a: int, b: int, c: int):
            return (a, b, c)

        s1 = MutableSignature(fn1)
        s1.reorder(2, 1, 0)

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

    class TestPackingParameter:
        """Tests related to packing multiple parameters into a single
        parameter."""

        def test_tuple_type_constructor(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)

            annots = [p.annotation for p in s]
            TupleType = tuple_type_constructor(annots)
            assert str(TupleType) == "typing.Tuple[int, typing.Any, int]"

        def test_named_tuple_type_constructor(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)

            annots = [p.annotation for p in s]
            TupleType = named_tuple_type_constructor(annots, ["a", "b", "c"])
            print(TupleType)

        def test_tuple_type_constructor2(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)

            class Foo(NamedTuple):
                a: int
                b: int
                c: int

            annots = [p.annotation for p in s]
            TupleType = tuple_type_constructor(annots, Foo)
            assert str(TupleType) == "typing.Tuple[int, typing.Any, int]"

        def test_mutable_parameter_tuple(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)
            MutableParameterTuple(list(s))

        # TODO: better tests here
        def test_mutable_parameter_tuple_by_name(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)
            s.pack(["a", "b"])
            print(s)
            print(s.to_signature())
            assert str(s.to_signature()) == "(a__b: Tuple[int, Any], c: int)"
            assert (
                str(s) == "<MutableSignature(a__b: Tuple[int, Any], c: int) -> _empty>"
            )

        def test_mutable_parameter_tuple_by_index(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)
            s.pack([0, 1])
            print(s)
            print(s.to_signature())
            assert str(s.to_signature()) == "(a__b: Tuple[int, Any], c: int)"
            assert (
                str(s) == "<MutableSignature(a__b: Tuple[int, Any], c: int) -> _empty>"
            )

        def test_mutable_parameter_tuple_by_name_and_index(self):
            def fn1(a: int, b, c: int):
                return (a, b, c)

            s = MutableSignature(fn1)
            s.pack([2, "a"])
            print(s)
            print(s.to_signature())
            assert str(s.to_signature()) == "(c__a: Tuple[int, int], b)"

        def test_pack_and_bind(self):
            def fn1(a: int, b, c: int):
                return a, b, c

            s = MutableSignature(fn1)
            s.pack((0, 1))
            fn2 = s.transform(fn1)
            assert fn2((1, 2), 3) == (1, 2, 3)

        def test_pack_and_bind_pos_1(self):
            def fn1(a: int, b, c: int):
                return a, b, c

            s = MutableSignature(fn1)
            s.pack((0, 1), position=1)
            fn2 = s.transform(fn1)
            assert fn2(3, (1, 2)) == (1, 2, 3)

        def test_pack_and_bind_doctest(self):
            def fn1(a: int, b: float, c: str, d: list) -> tuple:
                """Just returns a new tuple.

                :param a: Argument a
                :param b: Argument b
                :param c: Argument c
                :param d: Argument d
                :return: Returns a tuple of all the arguments
                """
                return a, b, c, d

            s = MutableSignature(fn1)
            s.pack(("a", "c", "d"), position=1)
            assert (
                str(s.to_signature())
                == "(b: float, a__c__d: Tuple[int, str, list]) -> tuple"
            )

            fn2 = s.transform(fn1)

            print(fn2.__doc__)

            expected = """
Transformed function

.. code-block:: python

    fn1(a: int, b: float, c: str, d: list) -> tuple

        Just returns a new tuple

        :param a: Argument a
        :param b: Argument b
        :param c: Argument c
        :param d: Argument d
        :return: Returns a tuple of all the arguments
""".strip(
                "\n"
            )
            assert fn2.__doc__ == expected
