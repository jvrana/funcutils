#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
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
        self._signature = Signature(self.params, **kwargs)
        return self._signature

    def get_param(self, key: Union[int, str], strict=True):
        for i, p in enumerate(self.params):
            if isinstance(key, int):
                if i == key:
                    if p.kind == Parameter.KEYWORD_ONLY and strict:
                        raise ValueError(
                            f"There is no positional parameter {i}. "
                            f"There is a Keyword-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return p
            else:
                if p.name == key:
                    if p.kind == Parameter.POSITIONAL_ONLY and strict:
                        raise ValueError(
                            f"There is no keyword parameter {key}. "
                            f"There is a Positional-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return p
        raise SignatureException(f"Could not find parameter '{key}'")

    def __getitem__(self, key) -> Parameter:
        return self.get_param(key)

    def __delitem__(self, key: Union[int, str]):
        return self._params.remove(self.get_param(key))

    def insert(self, index: int, param: Parameter):
        assert isinstance(param, Parameter)
        self._params.insert(index, param)

    def append(self, param: Parameter):
        assert isinstance(param, Parameter)
        self._params.append(param)

    def __len__(self):
        return len(self.params)

    def bind(self, args, kwargs) -> inspect.BoundArguments:
        return self.signature.bind(*args, **kwargs)

    def soft_bind(
        self, args, kwargs, ignore_params_from_signature: Optional[List[str]] = None
    ) -> SoftBoundParameters:
        return soft_bind(args, kwargs, ignore_params_from_signature)
