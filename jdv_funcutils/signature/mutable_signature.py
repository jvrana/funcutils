#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from __future__ import annotations

import functools
import inspect
import operator
import textwrap
from collections import OrderedDict
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import Collection
from typing import Dict
from typing import Generator
from typing import Generic
from typing import List
from typing import Literal
from typing import NamedTuple
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from jdv_funcutils.signature.utils import copy_signature
from jdv_funcutils.signature.utils import dict_remove_null
from jdv_funcutils.signature.utils import get_signature
from jdv_funcutils.utils import Null
from jdv_funcutils.utils import null
from jdv_funcutils.utils.repr_utils import ReprMixin
from jdv_funcutils.utils.textutils import extract_indent
from jdv_funcutils.utils.textutils import left_align


T = TypeVar("T")
SignatureLike = Union[Callable, Signature, List[Parameter]]
empty = inspect._empty


class SignatureException(Exception):
    ...


class SignatureMissingParameterException(Exception):
    ...


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


def _is_empty(x):
    return "_empty" in str(x)


def _to_annotations_tuple(annotations: List[Type]) -> Tuple[Type, ...]:
    annot_list = []
    for annot in annotations:
        if _is_empty(annot):
            annot = Any
        annot_list.append(annot)
    return tuple(annot_list)


def tuple_type_constructor(annotations_list: List[Any], tuple_cls=None) -> Type:
    annotations_list = _to_annotations_tuple(annotations_list)
    tuple_cls = Tuple or tuple_cls
    return tuple_cls[annotations_list]


def named_tuple_type_constructor(
    annotations_list: List[Any], names: List[str]
) -> NamedTuple:
    assert len(annotations_list) == len(names)
    name = "NamedTuple__" + "__".join(names)
    annotations_list = _to_annotations_tuple(annotations_list)
    tuple_fields = []
    for param_name, annot in zip(names, annotations_list):
        tuple_fields.append((param_name, annot))
    return NamedTuple(name, tuple_fields)


class ParameterLocation(NamedTuple):

    index: int
    relative_index_to_kind: int
    param: MutableParameter


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
        kwargs = dict(
            name=self.name,
            default=self.default,
            kind=self.kind,
            annotation=self.annotation,
        )
        return Parameter(**kwargs)

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

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.to_parameter()})>"


class MutableSignature(Sequence[MutableParameter]):

    ParameterKind = ParameterKind
    KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
    POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
    VAR_POSITIONAL = ParameterKind.VAR_POSITIONAL
    VAR_KEYWORD = ParameterKind.VAR_KEYWORD

    def __init__(
        self,
        obj: Optional[Union[Callable, Signature, List[Parameter]]] = None,
        return_annotation: Any = Null,
    ):
        self.param_by_kind = OrderedDict(
            {
                ParameterKind.POSITIONAL_ONLY: list(),
                ParameterKind.POSITIONAL_OR_KEYWORD: list(),
                ParameterKind.VAR_POSITIONAL: list(),
                ParameterKind.KEYWORD_ONLY: list(),
                ParameterKind.VAR_KEYWORD: list(),
            }
        )
        if obj:
            s = get_signature(obj, return_annotation=return_annotation)
            self.clear_and_add_all(s.parameters.values())
            return_annotation = s.return_annotation
        self.return_annotation = return_annotation

    def partition(
        self, fn: Callable[[MutableParameter], bool]
    ) -> Tuple[MutableSignature, MutableSignature]:
        """Partition the signature using a partition function.

        :param fn: The partition function taking a MutableParameter and returning a boolean.
        :return: Tuple of MutableSignature either passing the function (first in the tuple) or not passing the
            function (second in the tuple)
        """
        s1 = MutableSignature()
        s2 = MutableSignature()
        for p in self.params:
            if fn(p):
                s1.add(p)
            else:
                s2.add(p)
        s1.return_annotation = self.return_annotation
        s2.return_annotation = self.return_annotation
        return s1, s2

    @property
    def params(self) -> Tuple[MutableParameter, ...]:
        return tuple(functools.reduce(operator.add, self.param_by_kind.values()))

    def fix_signature(self):
        self.clear_and_add_all(self.params)

    def is_valid(self) -> bool:
        """Returns if parameters for a valid signature.

        If not, see `fix_signature` to fix and invalid signature.
        :return:
        """
        for k, v in self.param_by_kind.items():
            for p in v:
                if p.kind != k:
                    return False
        return True

    def clear_and_add_all(self, params: Collection[MutableParameter]):
        for k, v in self.param_by_kind.items():
            v.clear()
        for p in params:
            self.add(p)

    def get_signature_parameters(self) -> Tuple[Parameter]:
        return tuple([p.to_parameter() for p in self.params])

    def to_signature(self):
        kwargs = {}
        if self.return_annotation is not Null:
            kwargs["return_annotation"] = self.return_annotation
        params = [p.to_parameter() for p in self.params]
        return Signature(params, **kwargs, __validate_parameters__=True)

    def _enum_param_lists(self) -> Generator[ParameterLocation, None, None]:
        i = 0
        for kind, param_list in self.param_by_kind.items():
            for j, p in enumerate(param_list):
                yield ParameterLocation(i, j, p)
                i += 1

    def get_pos_and_param(
        self, key: Union[int, str, ParameterLike], strict=True
    ) -> ParameterLocation:
        for x in self._enum_param_lists():
            if isinstance(key, int):
                if x.index == key:
                    if x.param.kind == Parameter.KEYWORD_ONLY and strict:
                        raise SignatureMissingParameterException(
                            f"There is no positional parameter {x.index}. "
                            f"There is a Keyword-only parameter {x.param}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return x
            elif isinstance(key, str):
                if x.param.name == key:
                    if x.param.kind == Parameter.POSITIONAL_ONLY and strict:
                        raise SignatureMissingParameterException(
                            f"There is no keyword parameter {key}. "
                            f"There is a Positional-only parameter {x.param}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return x
            else:
                if (
                    x.param.name == key.name
                    and x.param.annotation == key.annotation
                    and x.param.kind == key.kind
                    and x.param.default == key.default
                ):
                    return x
        raise SignatureMissingParameterException(f"Could not find parameter '{key}'")

    def get_param(
        self, key: Union[int, str, ParameterLike], strict=True
    ) -> MutableParameter:
        return self.get_pos_and_param(key, strict=strict)[-1]

    def get_params(
        self, fn: Optional[Callable[[ParameterLike], bool]] = None
    ) -> Tuple[MutableParameter, ...]:
        if fn:
            return tuple([p for p in self.params if fn(p)])
        else:
            return tuple(self.params)

    def get_pos_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_positional)

    def get_pos_only_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_positional_only)

    def get_kw_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_keyword)

    def get_kw_only_params(self) -> Tuple[MutableParameter, ...]:
        return self.get_params(MutableParameter.is_keyword_only)

    def __len__(self):
        return len(self.params)

    def __getitem__(self, key: Union[str, int, ParameterLike]):
        return self.get_param(key)

    def __contains__(self, item: Union[int, str]):
        try:
            self.get_pos_and_param(item)
            return True
        except SignatureMissingParameterException:
            return False

    def __delitem__(self, key: Union[str, int, ParameterLike]):
        return self.remove(key)

    def _add(self, index: int, other: MutableParameter):
        if index == -1:
            self.param_by_kind[other.kind].append(other)
        else:
            self.param_by_kind[other.kind].insert(index, other)

    def _create_and_add_parameter(
        self,
        index: int,
        param: str,
        annotation: Any = Null,
        default: Any = null,
        kind: ParameterKind = null,
    ):
        kwargs = dict(annotation=annotation, default=default, kind=kind)
        kwargs = dict_remove_null(kwargs)
        if kwargs.get("kind", null) is Null:
            kwargs["kind"] = ParameterKind.POSITIONAL_OR_KEYWORD
        self._add(index, MutableParameter.from_parameter(Parameter(param, **kwargs)))

    def _add_parameter(self, index: int, param: Parameter, **kwargs):
        if kwargs:
            raise ValueError("add(param: Parameter) takes no additional arguments")
        return self._add(index, MutableParameter.from_parameter(param))

    def add(
        self,
        param: Union[str, MutableParameter, Parameter],
        annotation: Any = Null,
        *,
        default: Any = null,
        kind: ParameterKind = null,
        index: int = -1,
    ):
        kwargs = dict(annotation=annotation, default=default, kind=kind)
        kwargs = dict_remove_null(kwargs)
        if isinstance(param, str):
            return self._create_and_add_parameter(index, param, **kwargs)
        elif isinstance(param, Parameter):
            return self._add_parameter(index, param, **kwargs)
        elif isinstance(param, MutableParameter):
            if kwargs:
                raise ValueError(
                    "add(param: MutableParameter) takes no additional arguments"
                )
            return self._add(index, param)

    def insert(
        self,
        index: int,
        param: Union[str, MutableParameter, Parameter],
        annotation: Any = Null,
        *,
        default: Any = null,
        kind: ParameterKind = null,
    ):
        return self.add(param, annotation, default=default, kind=kind, index=index)

    def remove(self, param: Union[str, int, MutableParameter, Parameter]):
        param_to_delete = self.get_param(param)
        for i, j, p in self._enum_param_lists():
            plist = self.param_by_kind[p.kind]
            if p is param_to_delete:
                plist.remove(p)
                return
        raise IndexError(f"Could not remove '{param}'")

    def __str__(self):
        inner_str = ", ".join([str(p) for p in self.get_signature_parameters()])
        str_repr = f"<{self.__class__.__name__}({inner_str})"
        if self.return_annotation:
            str_repr += f" -> {self.return_annotation.__name__}"
        str_repr += ">"
        return str_repr

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        yield from self.params

    def pack(
        self,
        from_params: Sequence[Union[int, str]],
        name: Optional[str] = None,
        position: int = 0,
        kind=ParameterKind.POSITIONAL_OR_KEYWORD,
    ):
        """Pack a set of parameters into a single parameter.

        Examples:

        .. testsetup:: *

           import funcutils

        .. testcode::
            def fn1(a: int, b: float, c: str, d: list):
                return a, b, c, d

            s = MutableSignature(fn1)
            s.pack(('a', 'c', 'd'), position=1)
            str(s.to_signature())

        .. testoutput::

            (b: float, a__c__d: Tuple[int, str, list])

        :param from_params: Parameters to pack
        :param name: Optional name to give the new packed parameter.
            If not provided, parameter names will be joined with '__' (e.g. a, b, c => 'a__b__c')
        :param position: Position to insert the new packed parameter. Note that the position is
            relative to the parameter kind. PositionalOnly, PositionalOrKeyword, PositionalVar,
            KeywordOnly, KeywordVar
        :param kind: Parameter kind to give the new packed parameter.
        :return:
        """
        params = [self[k] for k in from_params]
        packed = MutableParameterTuple(params, name=name, kind=kind)

        to_remove = [self[k] for k in from_params]
        for p in to_remove:
            self.remove(p)
        self.insert(position, packed)

    def bind(self, *args, **kwargs) -> BoundSignature:
        return BoundSignature(self, *args, **kwargs)

    def reorder(self, *params):
        """Attempt to reorder the signature. Note that parameters of different
        kinds cannot be re-ordered.

        :param params:
        :return:
        """
        new_params = []
        for p in params:
            p2 = self.get_param(p)
            if p2 in new_params:
                raise SignatureException(f"Parameter '{p}' designated twice.")
            new_params.append(p2)
        assert len(new_params) == len(self)
        for k, v in self.param_by_kind.items():
            v.clear()
        for p in new_params:
            self.add(p)

    def transform(self, f: Callable, name: Optional[str] = None):
        s1 = self.__class__(f)
        b1 = s1.bind()

        name = name or f.__name__
        fdoc = f.__doc__ or ""
        fdoc = (
            f"New Signature: {name}{self.to_signature()}\n"
            + "\n"
            + left_align(f"{name}{inspect.signature(f)}:\n")
            + textwrap.indent(textwrap.dedent(fdoc), "    ").strip("\n")
        )

        @copy_signature(self.to_signature())
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            b2 = self.bind(*args, **kwargs)

            parameter_values = []
            i = 0
            for pv in b2.bound:
                if isinstance(pv.parameter, MutableParameterTuple):
                    for _param, _value in zip(pv.parameter.parameters, pv.value):
                        key = _param.name
                        if _param.is_positional_only():
                            key = i
                        parameter_values.append(
                            ParameterValue(key=key, value=_value, parameter=_param)
                        )
                else:
                    parameter_values.append(pv)

            for pv in parameter_values:
                b1.get(pv.parameter.name).value = pv.value
            return f(*b1.args, **b1.kwargs)

        wrapped.__doc__ = fdoc
        wrapped.__name__ = name
        return wrapped


class MutableParameterTuple(MutableParameter):
    def __init__(
        self,
        parameters: List[MutableParameter],
        annotation: Any = empty,
        name: Optional[str] = None,
        default: Tuple = empty,
        kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD,
    ):
        # super().__init__(name, default, annotation, kind)
        if name is not None:
            self.name = name
        else:
            self.name = "__".join([p.name for p in parameters])
        self.parameters = parameters
        if annotation == empty:
            annots = [p.annotation for p in parameters]
            names = [p.name for p in parameters]
            annotation = tuple_type_constructor(annots, names)
        self.annotation = annotation
        self.kind = kind
        if default is Null:
            if not any([_is_empty(p.default) for p in parameters]):
                default = [p.default for p in parameters]
        self.default = default


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


class BoundParameterValue(Protocol):

    key: Union[str, int]
    value: Any = (null,)
    parameter: MutableParameter = null

    def is_bound(self) -> Literal[True]:
        ...

    def is_unbound_value(self) -> Literal[False]:
        ...

    def is_unbound_param(self) -> Literal[False]:
        ...


class BoundSignature(Collection[ParameterValue]):
    def __init__(
        self, signature: Union[MutableSignature, SignatureLike], *args, **kwargs
    ):
        if not isinstance(signature, MutableSignature):
            signature = MutableSignature(signature)
        self.signature = signature
        self.data: List[ParameterValue] = []
        self.bind(*args, **kwargs)

    def partition(
        self, fn: Callable[[ParameterValue], bool]
    ) -> Tuple[BoundSignature, BoundSignature]:
        """Partition the signature using a partition function.

        :param fn: The partition function taking a ParameterValue and returning a boolean.
        :return: Tuple of BoundSignatures either passing the function (first in the tuple) or not passing the
            function (second in the tuple)
        """
        a, b = [], []
        for pv in self.data:
            if fn(pv):
                a.append(pv)
            else:
                b.append(pv)
        s1 = MutableSignature([p.parameter.to_parameter() for p in a])
        b1 = BoundSignature(s1)
        b1.data = a

        s2 = MutableSignature([p.parameter.to_parameter() for p in b])
        b2 = BoundSignature(s2)
        b2.data = b
        return b1, b2

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

    def get_args(self, bound: bool = True) -> Tuple[Any, ...]:
        return tuple(
            [
                x.value
                for x in self.data
                if (x.is_bound() is bound and isinstance(x.key, int))
            ]
        )

    def get_kwargs(self, bound: bool = True) -> Dict[str, Any]:
        return {
            x.parameter.name: x.value
            for x in self.data
            if (x.is_bound() is bound and isinstance(x.key, str))
        }

    @property
    def args(self) -> Tuple[Any, ...]:
        """Return the bound arguments as a tuple of values.

        :return:
        """
        return self.get_args(bound=True)

    @property
    def kwargs(self) -> Dict[str, Any]:
        """
        Return the bound keyword args as a dict of values
        :return:
        """
        return self.get_kwargs(bound=True)

    @property
    def bound(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if d.is_bound()])

    @property
    def unbound_parameters(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if d.is_unbound_param()])

    @property
    def unbound_values(self) -> Tuple[ParameterValue, ...]:
        return tuple([d for d in self.data if d.is_unbound_value()])

    @property
    def unbound_args(self) -> Tuple[Any, ...]:
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

    @property
    def unbound_kwargs(self) -> Dict[str, ParameterValue]:
        """
        Return the unbound keyword args as a dict of values
        :return:
        """
        return {
            x.parameter.name: x.value
            for x in self.data
            if (x.is_unbound_value() and isinstance(x.key, str))
        }

    def get(self, item: Union[int, str]) -> ParameterValue:
        for d in self.data:
            if d.parameter is not Null:
                if d.key == item or d.parameter.name == item:
                    return d

    def has_extra_args(self) -> bool:
        """Returns True if there are any unbound values.

        :return: bool
        """
        return len(self.get_unbound_values()) > 0

    def has_unbound_params(self) -> bool:
        """Return True if there are any unbound parameters.

        :return: bool
        """
        return len(self.get_unbound_parameters()) > 0

    def has_valid_signature(self) -> bool:
        """Return True if there are no unbound parameters.

        :return: bool
        """
        return not self.has_unbound_params()

    def is_valid(self):
        """Returns True if there are no unbound parameters and no unbound
        values.

        :return: bool
        """
        return not (self.has_unbound_params() or self.has_extra_args())

    def bound_signature(self, return_annotation=null) -> MutableSignature:
        if return_annotation is Null:
            return_annotation = self.signature.return_annotation
        parameters = [b.parameter.to_parameter() for b in self.bound]
        return MutableSignature(parameters, return_annotation=return_annotation)

    def unbound_signature(self, return_annotation=null) -> MutableSignature:
        if return_annotation is Null:
            return_annotation = self.signature.return_annotation
        parameters = [b.parameter.to_parameter() for b in self.unbound_parameters]
        return MutableSignature(parameters, return_annotation=return_annotation)

    def __getitem__(self, item: Union[str, int]) -> ParameterValue:
        return self.get(item)

    def __len__(self) -> int:
        return len(self.data)

    def __contains__(self, item: Union[str, int]) -> bool:
        for d in self.data:
            if item == d.key:
                return True
        return False

    def __iter__(self) -> Generator[ParameterValue, None, None]:
        yield from self.data
