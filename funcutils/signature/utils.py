#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from __future__ import annotations

import functools
import inspect
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import List
from typing import Tuple
from typing import Union

from funcutils.signature.typedefs import SignatureLike
from funcutils.utils import Null


def dict_rm_by_value(data: dict, fn: Callable) -> dict:
    return {k: v for k, v in data.items() if not fn(v)}


def dict_remove_null(data: dict) -> dict:
    return dict_rm_by_value(data, lambda x: x is Null)


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
