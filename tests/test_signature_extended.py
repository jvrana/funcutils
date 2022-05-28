#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import inspect

import pytest

from funcutils import SignatureException
from funcutils import SignatureExtended


class TestSignatureExtended:
    @pytest.fixture()
    def foo(self):
        def foo(a: int, b: int):
            ...

        return foo

    @pytest.fixture()
    def s(self, foo):
        s = SignatureExtended(foo)
        return s

    def test_get_param(self, s):
        assert s.get_param("b").name == "b"

        with pytest.raises(SignatureException, match="Could not find parameter 'c'"):
            s.get_param("c")

    def test_param_list(self, s, foo):
        assert s.params == tuple(inspect.signature(foo).parameters.values())

    def test_param_dict(self, s, foo):
        assert s.params == tuple(inspect.signature(foo).parameters.values())

    def test_del(self, s, foo):
        del s["a"]
        assert len(s) == 1
        assert s.params == tuple(inspect.signature(foo).parameters.values())[1:]

    def test_append(self, s, foo):
        s.append(
            inspect.Parameter(name="c", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        assert len(s) == 3
        assert list(s.signature.parameters.values())[0].name == "a"
        assert list(s.signature.parameters.values())[1].name == "b"
        assert list(s.signature.parameters.values())[2].name == "c"

    def test_insert(self, s, foo):
        s.insert(
            1, inspect.Parameter(name="c", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        assert len(s) == 3
        assert list(s.signature.parameters.values())[0].name == "a"
        assert list(s.signature.parameters.values())[1].name == "c"
        assert list(s.signature.parameters.values())[2].name == "b"

    def test_invalid_signature(self, s, foo):
        s.insert(1, inspect.Parameter(name="c", kind=inspect.Parameter.KEYWORD_ONLY))
        with pytest.raises(ValueError):
            s.signature

    def test_soft_bind(self):
        def foo(a: int, *, c: int = 4, d: int = 5):
            ...

        s = SignatureExtended(foo)

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
