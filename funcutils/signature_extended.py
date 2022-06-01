#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from __future__ import annotations

import functools
import inspect
import itertools
from collections import abc as cabc
from inspect import BoundArguments
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Protocol
from typing import Tuple
from typing import TypeVar
from typing import Union

from funcutils.null import Null
from funcutils.null import null
from funcutils.reprutils import ReprMixin
from funcutils.softbind import soft_bind
from funcutils.softbind import SoftBoundParameters

SignatureLike = Union[Callable, Signature, List[Parameter]]

T = TypeVar("T")


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
    def wrapped(self: MutableSignature, *args, **kwargs):
        self.validate()
        return f(self, *args, **kwargs)

    return wrapped


class ParameterKind:

    POSITIONAL_OR_KEYWORD = Parameter.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = Parameter.POSITIONAL_ONLY
    KEYWORD_ONLY = Parameter.KEYWORD_ONLY
    VAR_POSITIONAL = Parameter.VAR_POSITIONAL
    VAR_KEYWORD = Parameter.VAR_KEYWORD


class ParameterLike(Protocol):

    name: str
    default: Any
    annotation: any
    kind: ParameterKind


P = TypeVar("P", bound=ParameterLike)


class MutableParameter(ParameterLike):

    __slots__ = ["name", "default", "annotation", "kind"]
    POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
    KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
    VAR_POSITIONAL = ParameterKind.VAR_POSITIONAL
    VAR_KEYWORD = ParameterKind.VAR_KEYWORD

    def __init__(self, name: str, default: Any, annotation: Any, kind: ParameterKind):
        self.name = name
        self.default = default
        self.annotation = annotation
        self.kind = kind

    @classmethod
    def from_parameter(cls, param: Parameter) -> MutableParameter:
        return cls(
            name=param.name,
            default=param.default,
            annotation=param.annotation,
            kind=param.kind,
        )

    def to_parameter(self) -> Parameter:
        return Parameter(
            name=self.name,
            default=self.default,
            kind=self.kind,
            annotation=self.annotation,
        )

    def is_positional(self):
        return self.kind in [self.POSITIONAL_OR_KEYWORD, self.POSITIONAL_ONLY]

    def is_positional_only(self):
        return self.kind == self.POSITIONAL_ONLY

    def is_keyword(self):
        return self.kind in [self.POSITIONAL_OR_KEYWORD, self.KEYWORD_ONLY]

    def is_keyword_only(self):
        return self.kind == self.KEYWORD_ONLY

    def __str__(self):
        return f"<{self.__class__.__name__}({self.to_parameter()})>"


class MutableSignature:
    def __init__(
        self,
        obj: Union[Callable, Signature, List[Parameter]],
        return_annotation: Any = Null,
    ):
        s = get_signature(obj, return_annotation=return_annotation)
        self._params = [
            MutableParameter.from_parameter(p) for p in s.parameters.values()
        ]
        self.return_annotation = s.return_annotation

    def to_signature(self):
        kwargs = {}
        if self.return_annotation is not Null:
            kwargs["return_annotation"] = self.return_annotation
        params = [p.to_parameter() for p in self._params]
        return Signature(params, **kwargs, __validate_parameters__=True)

    def get_signature_parameters(self) -> Tuple[Parameter]:
        return tuple(self.to_signature().parameters.values())

    def get_param(self, key: Union[int, str], strict=True) -> MutableParameter:
        return self.get_pos_and_param(key, strict=strict)[1]

    def get_pos_and_param(
        self, key: Union[int, str], strict=True
    ) -> Tuple[int, MutableParameter]:
        for i, p in enumerate(self._params):
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

    def __getitem__(self, key) -> MutableParameter:
        return self.get_param(key)

    def __delitem__(self, key: Union[int, str]):
        return self._params.remove(self.get_param(key))

    def insert(self, index: int, param: Parameter) -> MutableSignature:
        assert isinstance(param, Parameter)
        self._params.insert(index, MutableParameter.from_parameter(param))
        return self

    def append(self, param: Parameter) -> MutableSignature:
        assert isinstance(param, Parameter)
        self._params.append(MutableParameter.from_parameter(param))
        return self

    @validate_signature
    def permute(self, *param_names: Union[int, str]) -> MutableSignature:
        assert len(param_names) == len(self)
        params = []
        for name in param_names:
            p = self[name]
            if p in params:
                raise SignatureException(f"Parameter '{p}' designated twice.")
            params.append(self[name])
        self._params = params

    def validate(self):
        self.to_signature()

    def get_params(
        self, fn: Optional[Callable[[ParameterLike], bool]] = None
    ) -> Tuple[MutableParameter, ...]:
        if fn:
            return tuple([p for p in self._params if fn(p)])
        else:
            return tuple(self._params)

    def get_pos_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_positional)

    def get_pos_only_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_positional_only)

    def get_kw_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_keyword)

    def get_kw_only_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_keyword_only)

    def __len__(self):
        return len(self._params)

    def __str__(self):
        inner_str = ", ".join([str(p) for p in self.get_signature_parameters()])
        str_repr = f"<{self.__class__.__name__}({inner_str})"
        if self.return_annotation:
            str_repr += f" -> {self.return_annotation.__name__}"
        str_repr += ">"
        return str_repr

    def __repr__(self):
        return self.__str__()

    def bind(self, *args, **kwargs) -> BoundSignature:
        return BoundSignature(self, *args, **kwargs)

    def transform(self, f: Callable, name: Optional[str] = None):
        s1 = self.__class__(f)
        b1 = s1.bind()

        name = name or f.__name__
        transform_doc = (
            f"Transformed function\n{name}{self.to_signature()} "
            f"==> {f.__name__}{s1.to_signature()}"
        )
        if f.__doc__:
            fdoc = "\n".join(transform_doc, f.__doc__)
        else:
            fdoc = transform_doc

        @copy_signature(self.to_signature())
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            b2 = self.bind(1, 2, 3)
            for pv in b2.get_bound():
                print(f"Setting {pv.parameter.name} to {pv.value}")
                b1.get(pv.parameter.name).value = pv.value
            return f(*b1.args, **b1.kwargs)

        wrapped.__doc__ = fdoc
        wrapped.__name__ = name
        return wrapped


class ParameterValue(ReprMixin, Generic[T]):
    __slots__ = ["key", "value", "parameter"]

    def __init__(
        self,
        key: Union[str, int],
        value: Any = null,
        parameter: Union[MutableParameter, Null] = null,
    ):
        assert not (value is Null and parameter is Null)
        self.key = key
        self.value = value
        self.parameter = parameter

    def is_bound(self):
        return self.value is not Null and self.parameter is not Null

    def is_unbound_value(self):
        return self.value is not Null and self.parameter is Null

    def is_unbound_param(self):
        return self.value is Null and self.parameter is not Null


class BoundSignature(MutableSignature):
    def __init__(
        self, signature: Union[MutableSignature, SignatureLike], *args, **kwargs
    ):
        if not isinstance(signature, MutableSignature):
            signature = MutableSignature(signature)
        self.signature = signature
        self.data: List[ParameterValue] = []
        self.bind(*args, **kwargs)

    def bind(self, *args, **kwargs) -> BoundSignature:
        data_dict = {}
        self.data.clear()
        for i, p in enumerate(self.signature.get_params()):
            if p.is_positional():
                keys = (i, p.name)
                v = ParameterValue(key=i, parameter=p)
            else:
                keys = (p.name,)
                v = ParameterValue(key=p.name, parameter=p)
            for k in keys:
                data_dict[k] = v
            self.data.append(v)

        visited = set()
        for i, arg in enumerate(args):
            if i in data_dict:
                pv = data_dict[i]
                assert pv not in visited
                pv.value = arg
                pv.key = i
                visited.add(pv)
            else:
                self.data.append(ParameterValue(key=i, value=arg))
        for k, v in kwargs.items():
            if k in data_dict:
                pv = data_dict[k]
                if pv in visited:
                    raise SignatureException(
                        f"\nInvalid Args: {self.__class__.__name__}.bind(*{args} **{kwargs})"
                        f"\n\tCannot set arg {k}='{v}' because it is already bound."
                        f"\n\t{pv}"
                    )
                pv.value = v
                pv.key = k
                visited.add(pv)
            else:
                self.data.append(ParameterValue(key=k, value=v))
        return self

    def get_args(self) -> Tuple[Any, ...]:
        """Return the bound arguments as a tuple of values.

        :return:
        """
        return tuple(
            [x.value for x in self.data if (x.is_bound() and isinstance(x.key, int))]
        )

    @property
    def args(self) -> Tuple[Any, ...]:
        """The bound arguments as a tuple of values.

        :return:
        """
        return self.get_args()

    def get_kwargs(self) -> Dict[str, Any]:
        """
        Return the bound keyword args as a dict of values
        :return:
        """
        return {
            x.parameter.name: x.value
            for x in self.data
            if (x.is_bound() and isinstance(x.key, str))
        }

    @property
    def kwargs(self) -> Dict[str, Any]:
        """
        The bound keyword args as a dict of values
        :return:
        """
        return self.get_kwargs()

    def get_bound(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if d.is_bound()])

    def get_unbound_parameters(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if not d.is_unbound_param()])

    def get_unbound_values(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if not d.is_unbound_value()])

    def get_unbound_args(self) -> Tuple[Any, ...]:
        """Return the unbound args as a tuple of values.

        :return:
        """
        return tuple(
            [
                x.value
                for x in self.data
                if (x.is_unbound_value() and isinstance(x.key, int))
            ]
        )

    def get_unbound_kwargs(self) -> Dict[str, Any]:
        """
        Return the unbound keyword args as a dict of values
        :return:
        """
        return {
            x.parameter.name: x.value
            for x in self.data
            if (x.is_unbound_value() and isinstance(x.key, str))
        }

    def get(self, item):
        for d in self.data:
            if d.parameter is not Null:
                if d.key == item or d.parameter.name == item:
                    return d
