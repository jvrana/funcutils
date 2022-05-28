#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import inspect
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple
from typing import Union


class SoftBoundParamValue:
    def __init__(self, key, value):
        self.key: Union[int, str] = key
        self.value: Any = value
        self.param: SoftBoundParam = None

    def bind(self, parameter):
        if self.param:
            if self.param is not parameter:
                raise ValueError(
                    f"Cannot rebind value to a different parameter.\n{self.param} != {parameter}"
                )
        self.param = parameter

    @classmethod
    def _from_args(cls, args):
        return [SoftBoundParamValue(i, v) for i, v in enumerate(args)]

    @classmethod
    def _from_kwargs(cls, kwargs):
        return [SoftBoundParamValue(k, v) for k, v in kwargs.items()]

    @classmethod
    def from_args_kwargs(cls, args, kwargs=None):
        insts = cls._from_args(args)
        if kwargs:
            insts.extend(cls._from_kwargs(kwargs))
        return insts

    def __str__(self):
        return f"<{self.__class__.__name__} key={self.key} param={self.param} value={self.value}>"

    def __repr__(self):
        return str(self)

    @property
    def is_bound(self):
        return self.param is not None


class SoftBoundParam:
    def __init__(self, param: Parameter, pos: int):
        self.parameter: Parameter = param
        self.pos: int = pos
        self.value: SoftBoundParamValue = None

    @classmethod
    def from_signature_or_parameters(
        cls, signature_or_parameters: Union[Signature, List[Parameter]]
    ):
        if isinstance(signature_or_parameters, Signature):
            parameters = list(signature_or_parameters.parameters.values())
        else:
            parameters = signature_or_parameters
        return [SoftBoundParam(v, i) for i, v in enumerate(parameters)]

    def bind(self, inst: SoftBoundParamValue):
        if self.value is not None and self.value is not inst:
            raise ValueError(
                f"Cannot rebind param value to a different value.\n{self.value} != {inst}"
            )
        self.value = inst

    @property
    def valid_keys(self):
        valid_keys = None
        if self.parameter.kind == Parameter.POSITIONAL_ONLY:
            valid_keys = (self.pos,)
        elif self.parameter.kind == Parameter.POSITIONAL_OR_KEYWORD:
            valid_keys = self.pos, self.parameter.name
        elif self.parameter.kind == Parameter.KEYWORD_ONLY:
            valid_keys = (self.parameter.name,)
        return valid_keys

    def __str__(self):
        v = "_empty"
        if self.value:
            v = self.value.value
        return (
            f'<{self.__class__.__name__} name="{self.parameter.name}" pos={self.pos} '
            f"value={v} kind={self.parameter.kind}>"
        )

    def __repr__(self):
        return str(self)

    @property
    def is_bound(self):
        return self.value is not None


class SoftBoundParameters(NamedTuple):
    params: List[SoftBoundParam]
    values: List[SoftBoundParamValue]

    def get_params(self, bound=None) -> List[SoftBoundParam]:
        params = self.params
        if bound is not None:
            params = [v for v in self.params if bound == v.is_bound]
        return params

    def get_param(self, key: Union[str, int]):
        for i, p in enumerate(self.params):
            if isinstance(key, int):
                if i == key:
                    if p.parameter.kind == Parameter.KEYWORD_ONLY:
                        raise ValueError(
                            f"There is no positional parameter {i}. "
                            f"There is a Keyword-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return p
            else:
                if p.parameter.name == key:
                    if p.parameter.kind == Parameter.POSITIONAL_ONLY:
                        raise ValueError(
                            f"There is no keyword parameter {key}. "
                            f"There is a Positional-only parameter {p}. "
                            f"Set `strict=False`, to return this parameter."
                        )
                    return p
        raise KeyError(f"Could not find parameter '{key}'")


    def get_values(self, bound=None) -> List[SoftBoundParamValue]:
        values = self.values
        if bound is not None:
            values = [v for v in self.values if bound == v.is_bound]
        return values

    @property
    def unbound_values(self) -> List[SoftBoundParamValue]:
        return self.get_values(bound=False)

    @property
    def bound_values(self) -> List[SoftBoundParamValue]:
        return self.get_values(bound=True)

    @property
    def unbound_params(self) -> List[SoftBoundParam]:
        return self.get_params(bound=False)

    @property
    def bound_params(self) -> List[SoftBoundParam]:
        return self.get_params(bound=True)

    def _signature(self, params: List[SoftBoundParam]) -> Signature:
        return Signature([p.parameter for p in params])

    def unbound_signature(self) -> Signature:
        return self._signature(self.unbound_params)

    def bound_signature(self) -> Signature:
        return self._signature(self.bound_params)

    def get_args(
        self, bound: bool = None, fn: Callable[[SoftBoundParamValue], bool] = None
    ) -> Tuple[Any, ...]:
        """Get positional arguments.

        :param bound: Whether to return only bound (True) elements or unbound args (False).
        By default returns all args.
        :param fn: Optional filter function
        :return: positional arguments
        """
        values = self.get_values(bound)
        return tuple(
            [
                v.value
                for v in values
                if isinstance(v.key, int) and (fn is None or fn(v))
            ]
        )

    def get_kwargs(
        self, bound: bool = None, fn: Callable[[SoftBoundParamValue], bool] = None
    ) -> Dict[str, Any]:
        """Get key-word arguments.

        :param bound: Whether to return only bound (True) elements or unbound args (False).
        By default returns all args.
        :param fn: Optional filter function
        :return: keyword arguments
        """
        values = self.get_values(bound)
        return {
            v.key: v.value
            for v in values
            if isinstance(v.key, str) and (fn is None or fn(v))
        }

    @classmethod
    def bind(
        cls,
        signature_params_or_fn: Union[Signature, Callable, List[Parameter]],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        ignore_params_from_signature: Optional[List[str]] = None,
    ):
        """Attempt to bind parameters from a call signature to provided
        parameter values (args, kwargs). Resulting parameters and values can be
        partitioned by whether they were bound.

        Usage

        .. code-blocK:: python
            def foo(a: int, *, c: int = 4, d: int = 5):
                ...

            s = inspect.signature(foo)

            args = (1, 2, 3)
            kwargs = {'c': 5}

            ret = soft_bind(s, args, kwargs)

            assert len(ret.get_params(bound=True)) == 2
            assert len(ret.get_params(bound=False)) == 1
            assert len(ret.get_values(bound=True)) == 2
            assert len(ret.get_values(bound=False)) == 2

            bound_params = soft_bind(foo)

            # get all values
            all_values: List[SoftBoundParamValue] = bound_params.get_values()
            unbound_values = bound_params.get_values(bound=False)
            bound_values = bound_params.get_values(bound=True)

            # get all parameters
            all_params: List[SoftBoundParam] = bound_params.get_params() # get all parameters

            # get all parameters not bound to a value
            unbound_params = bound_params.get_params(bound=False)

            # get all parameters bound to a values
            bound_params = bound_params.get_params(bound=True)

            # parameters and values are bound to each other
            param0 = ret.get_params(bound=True)[0]
            value0 = ret.get_values(bound=True)[0]
            param0.value is value0
            value0.param is param0

            print(param0)
            # <SoftBoundParam name="a" pos=0 value=1 kind=POSITIONAL_OR_KEYWORD>

            print(value0)
            # <SoftBoundParamValue key=0 param=<SoftBoundParam name="a" pos=0 value=1 \
            # kind=POSITIONAL_OR_KEYWORD> value=1>

        :param signature:
        :param args:
        :param kwargs:
        :return:
        """
        signature = signature_params_or_fn
        if inspect.ismethod(signature_params_or_fn) or inspect.isfunction(
            signature_params_or_fn
        ):
            signature = inspect.signature(signature_params_or_fn)

        if ignore_params_from_signature:
            _params = signature.parameters.values()
            _new_params_list = []
            for p in _params:
                if p.name not in ignore_params_from_signature:
                    _new_params_list.append(p)
            signature = Signature(_new_params_list)

        values = SoftBoundParamValue.from_args_kwargs(args, kwargs)
        params = SoftBoundParam.from_signature_or_parameters(signature)
        for val in values:
            for param in params:
                if val.key in param.valid_keys:
                    val.bind(param)
                    param.bind(val)
        return cls(params, values)


soft_bind = SoftBoundParameters.bind
