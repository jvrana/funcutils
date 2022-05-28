#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from __future__ import annotations
import functools
import inspect
from inspect import BoundArguments
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from funcutils.null import Null
from funcutils.softbind import soft_bind
from funcutils.softbind import SoftBoundParameters

SignatureLike = Union[Callable, Signature, List[Parameter]]


class SignatureException(Exception):
    ...


def ignore_params(
    s: Signature, ignore: Union[str, Tuple[str, ...], List[str], None] = None
) -> Signature:
    if isinstance(ignore, str):
        ignore = (ignore,)
    if ignore:
        parameters = []
        for _, p in s.parameters.items():
            p: Parameter
            if p.name in ignore:
                continue
            parameters.append(p)
        s = Signature(parameters, return_annotation=s.return_annotation)
    return s


def get_signature(
    obj: SignatureLike,
    return_annotation: Any = Null,
    ignore: Union[str, Tuple[str, ...], List[str], None] = None,
) -> Signature:
    if isinstance(obj, list):
        kwargs = {}
        if return_annotation is not Null:
            kwargs["return_annotation"] = return_annotation
        signature = Signature(obj, **kwargs)
    elif isinstance(obj, Signature):
        signature = obj
    else:
        signature = inspect.signature(obj)
    signature = ignore_params(signature, ignore=ignore)
    return signature


def signature_to_param_list(s: Signature):
    return list(dict(s.parameters).values())


def signature_to_param_dict(s: Signature):
    return dict(s.parameters)


def copy_signature(
    obj: SignatureLike,
    return_annotation: Any = Null,
    ignore: Union[str, Tuple[str, ...], List[str], None] = None,
):
    signature = get_signature(obj, return_annotation=return_annotation, ignore=ignore)
    if isinstance(ignore, str):
        ignore = (ignore,)
    if ignore:
        parameters = []
        for _, p in signature.parameters.items():
            p: Parameter
            if p.name in ignore:
                continue
            parameters.append(p)
        signature = Signature(parameters)

    def wrapped(fn):
        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        _wrapped.__signature__ = signature
        return _wrapped

    return wrapped


def validate_signature(f):
    @functools.wraps(f)
    def wrapped(self: SignatureExtended, *args, **kwargs):
        self.signature
        return f(self, *args, **kwargs)
    return wrapped


class SignatureExtended:
    def __init__(
        self,
        obj: Union[Callable, Signature, List[Parameter]],
        return_annotation: Any = Null,
    ):
        self._signature = get_signature(obj, return_annotation=return_annotation)
        self._params = list(self._signature.parameters.values())
        self.return_annotation = self._signature.return_annotation

    @property
    def params(self) -> Tuple[Parameter, ...]:
        return tuple(self._params)

    @property
    def signature(self):
        kwargs = {}
        if self.return_annotation is not Null:
            kwargs["return_annotation"] = self.return_annotation
        self._signature = Signature(self.params, **kwargs, __validate_parameters__=True)
        return self._signature

    def get_param(self, key: Union[int, str], strict=True) -> Parameter:
        return self.get_pos_and_param(key, strict=strict)[1]

    def get_pos_and_param(self, key: Union[int, str], strict=True) -> Tuple[int, Parameter]:
        for i, p in enumerate(self.params):
            if isinstance(key, int):
                if i == key:
                    if p.kind == Parameter.KEYWORD_ONLY and strict:
                        raise ValueError(
                            f"There is no positional parameter {i}. "
                            f"There is a Keyword-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return i, p
            else:
                if p.name == key:
                    if p.kind == Parameter.POSITIONAL_ONLY and strict:
                        raise ValueError(
                            f"There is no keyword parameter {key}. "
                            f"There is a Positional-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return i, p
        raise SignatureException(f"Could not find parameter '{key}'")

    def __getitem__(self, key) -> Parameter:
        return self.get_param(key)

    def __delitem__(self, key: Union[int, str]):
        return self._params.remove(self.get_param(key))

    def insert(self, index: int, param: Parameter) -> SignatureExtended:
        assert isinstance(param, Parameter)
        self._params.insert(index, param)
        return self

    def append(self, param: Parameter) -> SignatureExtended:
        assert isinstance(param, Parameter)
        self._params.append(param)
        return self

    def __len__(self):
        return len(self.params)

    def bind(self, *args, **kwargs) -> inspect.BoundArguments:
        if kwargs is None:
            kwargs = dict()
        return self.signature.bind(*args, **kwargs)

    def soft_bind(self, *args, **kwargs) -> SoftBoundParameters:
        return soft_bind(
            self.signature,
            args,
            kwargs
        )

    # TODO: deprecated?
    @validate_signature
    def permute(self, *param_names: Union[int, str]) -> SignatureExtended:
        assert len(param_names) == len(self.params)
        params = []
        for name in param_names:
            p = self[name]
            if p in params:
                raise SignatureException(f"Parameter '{p}' designated twice.")
            params.append(self[name])
        self._params = params

    def __str__(self):
        inner_str = ', '.join([str(p) for p in self.params])
        str_repr = f"<{self.__class__.__name__}({inner_str})"
        if self.return_annotation:
            str_repr += f' -> {self.return_annotation.__name__}'
        str_repr += '>'
        return str_repr

    def __repr__(self):
        return self.__str__()