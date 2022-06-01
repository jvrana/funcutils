import functools
import operator
from collections import OrderedDict
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple
from typing import Union

from funcutils import MutableParameter
from funcutils.signature.mutable_signature import ParameterKind
from funcutils.signature.mutable_signature import ParameterLike
from funcutils.signature.mutable_signature import SignatureMissingParameterException
from funcutils.utils import Null
from funcutils.utils import null


def dict_rm_by_value(data: dict, fn: Callable) -> dict:
    return {k: v for k, v in data.items() if not fn(v)}


def dict_remove_null(data: dict) -> dict:
    return dict_rm_by_value(data, lambda x: x is Null)


class ParameterLocation(NamedTuple):

    index: int
    relative_index_to_kind: int
    param: MutableParameter


class ParametersView:
    ParameterKind = ParameterKind
    KEYWORD_ONLY = ParameterKind.KEYWORD_ONLY
    POSITIONAL_OR_KEYWORD = ParameterKind.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY = ParameterKind.POSITIONAL_ONLY
    VAR_POSITIONAL = ParameterKind.VAR_POSITIONAL
    VAR_KEYWORD = ParameterKind.VAR_KEYWORD

    def __init__(self):
        self.param_by_kind = OrderedDict(
            {
                ParameterKind.POSITIONAL_ONLY: list(),
                ParameterKind.POSITIONAL_OR_KEYWORD: list(),
                ParameterKind.VAR_POSITIONAL: list(),
                ParameterKind.KEYWORD_ONLY: list(),
                ParameterKind.VAR_KEYWORD: list(),
            }
        )

    @property
    def params(self) -> Tuple[MutableParameter, ...]:
        return tuple(functools.reduce(operator.add, self.param_by_kind.values()))

    def _enum_param_lists(self) -> Generator[ParameterLocation, None, None]:
        i = 0
        for kind, param_list in self.param_by_kind.items():
            for j, p in enumerate(param_list):
                yield ParameterLocation(i, j, p)
                i += 1

    def _find_param(self, key: Union[int, str, ParameterLike], strict=True):
        for x in self._enum_param_lists():
            if isinstance(key, int):
                if x.index == key:
                    if x.kind == Parameter.KEYWORD_ONLY and strict:
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
                    x.param == key.name
                    and x.param.annotation == x.param.annotation
                    and x.param.kind == key.kind
                    and x.param.default == key.default
                ):
                    return x
        raise SignatureMissingParameterException(f"Could not find parameter '{key}'")

    def get_pos_and_param(
        self, key: Union[int, str, ParameterLike], strict=True
    ) -> Tuple[int, MutableParameter]:
        for i, j, p in enumerate(self.params):
            if isinstance(key, int):
                if i == key:
                    if p.kind == Parameter.KEYWORD_ONLY and strict:
                        raise SignatureMissingParameterException(
                            f"There is no positional parameter {i}. "
                            f"There is a Keyword-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return ParameterLocation(i, j, p)
            elif isinstance(key, str):
                if p.name == key:
                    if p.kind == Parameter.POSITIONAL_ONLY and strict:
                        raise SignatureMissingParameterException(
                            f"There is no keyword parameter {key}. "
                            f"There is a Positional-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return ParameterLocation(i, j, p)
            else:
                if (
                    p.name == key.name
                    and p.annotation == key.annotation
                    and p.kind == key.kind
                    and p.default == key.default
                ):
                    return ParameterLocation(i, j, p)
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


def test_():
    x = ParametersView()
    print(x.params)
    print(x.params)
    x.add("a", int)
    x.add("b", int)
    x.add("c", float, kind=x.POSITIONAL_ONLY)
    x.add("d", float, kind=x.KEYWORD_ONLY, default=5.0)
    print(Signature([p.to_parameter() for p in x.params]))
