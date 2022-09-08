#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from __future__ import annotations

import functools
import inspect
import operator
import textwrap
import typing
from collections import OrderedDict
from inspect import _ParameterKind  # noqa
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import Collection
from typing import Dict
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from jdv_funcutils.imports import empty
from jdv_funcutils.signature.utils import copy_signature
from jdv_funcutils.signature.utils import dict_remove_null
from jdv_funcutils.signature.utils import get_signature
from jdv_funcutils.utils import Null
from jdv_funcutils.utils import null
from jdv_funcutils.utils.repr_utils import ReprMixin
from jdv_funcutils.utils.textutils import left_align

_T = TypeVar("_T")
_Type = TypeVar("_Type", bound=Type[object])

SignatureLike = Union[Callable[..., Any], Signature, List[Parameter]]


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
    annotation: Any
    kind: _ParameterKind


def _is_empty(x: Any) -> bool:
    return "_empty" in str(x)


def _to_annotations_tuple(
    annotations: Sequence[Type[object]],
) -> Tuple[Type[object], ...]:
    annot_list: List[Type[object]] = []
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
    annotations_list: Sequence[Any], names: List[str]
) -> Type[NamedTuple]:
    assert len(annotations_list) == len(names)
    name = "NamedTuple__" + "__".join(names)
    annotations_list = _to_annotations_tuple(annotations_list)
    tuple_fields: List[Tuple[str, Any]] = []
    for param_name, annot in zip(names, annotations_list):
        tuple_fields.append((param_name, annot))
    return NamedTuple(name, tuple_fields)


class ParameterLocation(NamedTuple):

    param_index: int
    relative_index_to_kind: int
    param: MutableParameter


class MutableParameter(ParameterLike):

    __slots__ = ["name", "default", "annotation", "kind"]
    POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
    KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
    VAR_POSITIONAL = ParameterKind.VAR_POSITIONAL
    VAR_KEYWORD = ParameterKind.VAR_KEYWORD

    def __init__(self, name: str, default: Any, annotation: Any, kind: _ParameterKind):
        self.name = name
        self.default = default
        self.annotation = annotation
        self.kind: _ParameterKind = kind

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

    def __eq__(self, other: object):
        if not isinstance(other, MutableParameter):
            return False
        if not self.name == other.name:
            return False
        if not self.kind == other.kind:
            return False
        if not self.default == other.default:
            return False
        if not self.annotation == other.annotation:
            return False
        return True

    def __str__(self):
        return f"<{self.__class__.__name__}({self.to_parameter()})>"

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.to_parameter()})>"


_Param = Union[Parameter, MutableParameter]


class MutableSignature(Sequence[MutableParameter]):

    ParameterKind = ParameterKind
    KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
    POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
    VAR_POSITIONAL = ParameterKind.VAR_POSITIONAL
    VAR_KEYWORD = ParameterKind.VAR_KEYWORD

    def __init__(
        self,
        obj: Optional[Union[Callable[..., Any], Signature, List[Parameter]]] = None,
        return_annotation: Any = Null,
    ):
        self.param_by_kind: OrderedDict[
            _ParameterKind, List[MutableParameter]
        ] = OrderedDict(
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
            self.clear_and_add_all(list(s.parameters.values()))
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

    def clear_and_add_all(self, params: Sequence[_Param]):
        for v in self.param_by_kind.values():
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
        for param_list in self.param_by_kind.values():
            for j, p in enumerate(param_list):
                yield ParameterLocation(i, j, p)
                i += 1

    def get_pos_and_param(
        self, key: Union[int, str, _Param], strict: bool = True
    ) -> ParameterLocation:
        for x in self._enum_param_lists():
            if isinstance(key, int):
                if x.param_index == key:
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
        self, key: Union[int, str, _Param], strict: bool = True
    ) -> MutableParameter:
        return self.get_pos_and_param(key, strict=strict)[-1]

    def get_params(
        self, fn: Optional[Callable[[_Param], bool]] = None
    ) -> Tuple[MutableParameter, ...]:
        if fn:
            return tuple([p for p in self.params if fn(p)])
        else:
            return tuple(self.params)

    def get_pos_params(self) -> Tuple[MutableParameter, ...]:
        fn = typing.cast(
            Callable[[_Param], bool],
            MutableParameter.is_positional,
        )
        return self.get_params(fn)

    def get_pos_only_params(self) -> Tuple[MutableParameter, ...]:
        fn = typing.cast(
            Callable[[_Param], bool],
            MutableParameter.is_positional_only,
        )
        return self.get_params(fn)

    def get_kw_params(self) -> Tuple[MutableParameter, ...]:
        fn = typing.cast(
            Callable[[_Param], bool],
            MutableParameter.is_keyword,
        )
        return self.get_params(fn)

    def get_kw_only_params(self) -> Tuple[MutableParameter, ...]:
        fn = typing.cast(Callable[[_Param], bool], MutableParameter.is_keyword_only)
        return self.get_params(fn)

    def __len__(self):
        return len(self.params)

    def __getitem__(self, key: Union[str, int, _Param]):
        return self.get_param(key)

    def __contains__(self, item: Union[int, str]):
        try:
            self.get_pos_and_param(item)
            return True
        except SignatureMissingParameterException:
            return False

    def __delitem__(self, key: Union[str, int, _Param]):
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
        kind: Union[Null, ParameterKind] = null,
    ):
        kwargs = dict(annotation=annotation, default=default, kind=kind)
        kwargs = dict_remove_null(kwargs)
        if kwargs.get("kind", null) is Null:
            kwargs["kind"] = ParameterKind.POSITIONAL_OR_KEYWORD
        self._add(index, MutableParameter.from_parameter(Parameter(param, **kwargs)))

    def _add_parameter(self, index: int, param: Parameter, **kwargs: Any):
        if kwargs:
            raise ValueError("add(param: Parameter) takes no additional arguments")
        return self._add(index, MutableParameter.from_parameter(param))

    def add(
        self,
        param: Union[str, MutableParameter, Parameter],
        annotation: Any = Null,
        *,
        default: Any = null,
        kind: Union[Null, ParameterKind] = null,
        index: int = -1,
    ):
        kwargs = dict(annotation=annotation, default=default, kind=kind)
        kwargs = dict_remove_null(kwargs)
        if isinstance(param, str):
            return self._create_and_add_parameter(index, param, **kwargs)
        elif isinstance(param, Parameter):
            return self._add_parameter(index, param, **kwargs)
        elif isinstance(param, MutableParameter):  # noqa
            if kwargs:
                raise ValueError(
                    "add(param: MutableParameter) takes no additional arguments"
                )
            return self._add(index, param)
        raise TypeError("param must be str, Parameter, MutableParameters")

    def insert(
        self,
        index: int,
        param: Union[str, MutableParameter, Parameter],
        annotation: Any = Null,
        *,
        default: Any = null,
        kind: Union[Null, ParameterKind] = null,
    ):
        return self.add(param, annotation, default=default, kind=kind, index=index)

    def remove(self, param: Union[str, int, MutableParameter, Parameter]):
        param_to_delete = self.get_param(param)
        for _i, _j, p in self._enum_param_lists():
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
        kind: _ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD,
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

    def bind(self, *args: Any, **kwargs: Any) -> BoundSignature:  # noqa
        return BoundSignature(self, *args, **kwargs)

    def reorder(self, *params: Union[int, str, Parameter, MutableParameter]):
        """Attempt to reorder the signature. Note that parameters of different
        kinds cannot be re-ordered.

        :param params:
        :return:
        """
        new_params: List[MutableParameter] = []
        for p in params:
            p2 = self.get_param(p)
            if p2 in new_params:
                raise SignatureException(f"Parameter '{p}' designated twice.")
            new_params.append(p2)
        assert len(new_params) == len(self)
        for v in self.param_by_kind.values():
            v.clear()
        for p in new_params:
            self.add(p)

    def transform(self, f: Callable[..., _T], name: Optional[str] = None):
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
        def wrapped(*args: Any, **kwargs: Any):
            b2 = self.bind(*args, **kwargs)

            parameter_values: List[BoundParamValue] = []
            i = 0
            for pv in b2.bound:
                if isinstance(pv.mutable_parameter, MutableParameterTuple):
                    for _param, _value in zip(
                        pv.mutable_parameter.parameters, pv.value
                    ):
                        key = _param.name
                        if _param.is_positional_only():
                            key = i
                        parameter_values.append(
                            typing.cast(
                                BoundParamValue,
                                ParameterValue(
                                    key=key, value=_value, mutable_parameter=_param
                                ),
                            )
                        )
                else:
                    parameter_values.append(pv)

            for pv in parameter_values:
                param_value2 = b1.get(pv.mutable_parameter.name)
                if param_value2 is not None:
                    param_value2.value = pv.value
                else:
                    raise ValueError(f"Could not find parameter value for {pv.name}")
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
        default: Any = empty,
        kind: _ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD,
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


class ParameterValue(ReprMixin):
    __slots__ = ["key", "value", "mutable_parameter"]

    def __init__(
        self,
        key: Union[str, int],
        value: Any = null,
        mutable_parameter: Union[MutableParameter, Null] = null,
    ):
        assert not (value is Null and mutable_parameter is Null)
        self.key = key
        self.value = value
        self.mutable_parameter = mutable_parameter

    @property
    def name(self) -> Union[None, str]:
        if self.mutable_parameter is not Null:
            return self.mutable_parameter.name  # noqa

    def is_bound(self) -> bool:
        """Returns true if Parameter has value and parameter defined.

        :return:
        """
        return self.value is not Null and self.mutable_parameter is not Null

    def is_missing_parameter(self) -> bool:
        """Returns True if ParameterValue has a value defined but no parameter
        associated.

        :return:
        """
        return self.value is not Null and self.mutable_parameter is Null

    def is_missing_value(self) -> bool:
        """Returns True if ParameterValue has a parameter associated but no
        value.

        :return:
        """
        return self.value is Null and self.mutable_parameter is not Null

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterValue):
            return False

        def compare(a: Any, b: Any) -> bool:
            if a is Null and b is Null:
                return True
            return a == b

        if not compare(self.key, other.key):
            return False
        if not compare(self.value, other.value):
            return False
        if not compare(self.mutable_parameter, other.mutable_parameter):
            return False
        return True


class BoundParamValue(ParameterValue):
    key: Union[str, int]
    value: Any
    mutable_parameter: MutableParameter


class ParamValueMissingParam(ParameterValue):
    key: Union[str, int]
    value: Any
    mutable_parameter: Null


class ParamValueMissingValue(ParameterValue):
    key: Union[str, int]
    value: Null
    mutable_parameter: MutableParameter


class BoundSignature(Collection[ParameterValue]):
    def __init__(
        self,
        signature: Union[MutableSignature, SignatureLike],
        *args: Any,
        **kwargs: Any,
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
        param_val_list_a: List[ParameterValue] = []
        param_val_list_b: List[ParameterValue] = []
        for pv in self.data:
            if fn(pv):
                param_val_list_a.append(pv)
            else:
                param_val_list_b.append(pv)

        bound_sign_a = self._create_bound_signature_from_pvalue_list(param_val_list_a)
        bound_sign_b = self._create_bound_signature_from_pvalue_list(param_val_list_b)
        return bound_sign_a, bound_sign_b

    def _extract_params_from_pvalue_list(
        self, param_values: List[ParameterValue]
    ) -> List[Parameter]:
        params: List[Parameter] = []
        for param_value in param_values:
            if param_value.mutable_parameter is not Null:
                mutable_param = typing.cast(
                    MutableParameter, param_value.mutable_parameter
                )
                params.append(mutable_param.to_parameter())
        return params

    def _create_bound_signature_from_pvalue_list(
        self, param_values: List[ParameterValue]
    ) -> BoundSignature:
        param_list = self._extract_params_from_pvalue_list(param_values)
        mut_sign = MutableSignature(param_list)
        bound_sign: BoundSignature = BoundSignature(mut_sign)
        bound_sign.data = param_values
        return bound_sign

    def bind(self, *args: Any, **kwargs: Any) -> BoundSignature:
        data_dict: Dict[typing.Hashable, ParameterValue] = {}
        self.data.clear()
        for i, p in enumerate(self.signature.get_params()):
            if p.is_positional():
                keys = (i, p.name)
                v: ParameterValue = ParameterValue(key=i, mutable_parameter=p)
            else:
                keys = (p.name,)
                v: ParameterValue = ParameterValue(key=p.name, mutable_parameter=p)
            for k in keys:
                data_dict[k] = v
            self.data.append(v)

        visited: typing.Dict[Union[int, str], ParameterValue] = dict()
        for i, arg in enumerate(args):
            if i in data_dict:
                pv = data_dict[i]
                assert pv.key not in visited
                pv.value = arg
                pv.key = i
                visited[pv.key] = pv
            else:
                self.data.append(ParameterValue(key=i, value=arg))
        for k, v in kwargs.items():
            if k in data_dict:
                pv = data_dict[k]
                if pv in visited.values():
                    raise SignatureException(
                        f"\nInvalid Args: {self.__class__.__name__}.bind(*{args} **{kwargs})"
                        f"\n\tCannot set arg {k}='{v}' because it is already bound."
                        f"\n\t{pv}"
                    )
                pv.value = v
                pv.key = k
                visited[pv.key] = pv
            else:
                self.data.append(ParameterValue(key=k, value=v))
        return self

    def get_args(self, bound: bool = True) -> Tuple[Any, ...]:
        pos_param_values: List[ParameterValue] = list()
        max_index = -1

        for param_value in self.data:
            if param_value.is_bound() is bound and isinstance(param_value.key, int):
                pos_param_values.append(param_value)
                if param_value.key > max_index:
                    max_index = param_value.key

        pos_args = [Null] * (max_index + 1)
        for param_value in pos_param_values:
            pos_args[int(param_value.key)] = param_value.value
        return tuple(pos_args)

    def get_kwargs(self, bound: bool = True) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        for param_value in self.data:
            if param_value.is_bound() is bound and isinstance(param_value.key, str):
                kwargs[param_value.key] = param_value.value
        return kwargs

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
    def bound(self) -> Tuple[BoundParamValue, ...]:
        return tuple(
            [typing.cast(BoundParamValue, d) for d in self.data if d.is_bound()]
        )

    @property
    def params_missing_values(self) -> Tuple[ParamValueMissingValue, ...]:
        return tuple(
            [
                typing.cast(ParamValueMissingValue, d)
                for d in self.data
                if d.is_missing_value()
            ]
        )

    @property
    def values_missing_params(self) -> Tuple[ParamValueMissingParam, ...]:
        return tuple(
            [
                typing.cast(ParamValueMissingParam, d)
                for d in self.data
                if d.is_missing_parameter()
            ]
        )

    @property
    def args_missing_params(self) -> Tuple[Any, ...]:
        """Return the unbound args as a tuple of values.

        :return:
        """
        pos_param_values: List[ParameterValue] = list()

        for param_value in self.data:
            if param_value.is_missing_parameter() is True and isinstance(
                param_value.key, int
            ):
                pos_param_values.append(param_value)
        return tuple(p.value for p in pos_param_values)

    @property
    def kwargs_missing_params(self) -> Dict[str, Any]:
        """
        Return the unbound keyword args as a dict of values
        :return:
        """
        kwargs: Dict[str, Any] = {}
        for param_value in self.data:
            if param_value.is_missing_parameter() is True and isinstance(
                param_value.key, str
            ):
                kwargs[param_value.key] = param_value.value
        return kwargs

    def get(self, item: Union[int, str]) -> Optional[ParameterValue]:
        for d in self.data:
            if d.mutable_parameter is not Null:
                if d.key == item or d.name == item:
                    return d

    def has_extra_args(self) -> bool:
        """Returns True if there are any unbound values.

        :return: bool
        """
        return len(self.values_missing_params) > 0

    def has_missing_values(self) -> bool:
        """Return True if there are any unbound parameters.

        :return: bool
        """
        return len(self.params_missing_values) > 0

    def has_valid_signature(self) -> bool:
        """Return True if there are no unbound parameters.

        :return: bool
        """
        return not self.has_missing_values()

    def is_valid(self):
        """Returns True if there are no unbound parameters and no unbound
        values.

        :return: bool
        """
        return not (self.has_missing_values() or self.has_extra_args())

    def bound_signature(self, return_annotation: Any = null) -> MutableSignature:
        if return_annotation is Null:
            return_annotation = self.signature.return_annotation
        parameters = [b.mutable_parameter.to_parameter() for b in self.bound]
        return MutableSignature(parameters, return_annotation=return_annotation)

    def unbound_signature(self, return_annotation: Any = null) -> MutableSignature:
        if return_annotation is Null:
            return_annotation = self.signature.return_annotation
        parameters = [
            b.mutable_parameter.to_parameter() for b in self.params_missing_values
        ]
        return MutableSignature(parameters, return_annotation=return_annotation)

    def __getitem__(self, item: Union[str, int]) -> Union[None, ParameterValue]:
        return self.get(item)

    def __len__(self) -> int:
        return len(self.data)

    def __contains__(self, item: object) -> bool:
        for d in self.data:
            if item == d.key:
                return True
        return False

    def __iter__(self) -> Generator[ParameterValue, None, None]:
        yield from self.data
