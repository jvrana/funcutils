from typing import Any
from typing import Literal
from typing import Type
from typing import TypeVar
from typing import Union

SINGLETON: Literal["__singleton__"] = "__singleton__"
SINGLETON_INST: Literal["__singleton_inst__"] = "__singleton_inst__"


Singleton = TypeVar("Singleton", bound=Type)


def singleton(c: Union[Type, str]) -> Singleton:
    if isinstance(c, str):
        c = type(c, (object,), {})

    def __new__(cls, *args, **kwargs):
        if getattr(cls, SINGLETON_INST) is None:
            new = c.__new__(cls)
            setattr(cls, SINGLETON_INST, new)
            new.__init__(*args, **kwargs)
        return getattr(cls, SINGLETON_INST)

    def __call__(self, *args, **kwargs):
        return self

    # def __str__(self):
    #     return self.__class__.__name__
    #
    # def __repr__(self):
    #     return self.__class__.__name__

    return type(
        c.__name__,
        (c,),
        {
            "__new__": __new__,
            "__call__": __call__,
            # '__str__': __str__,
            # '__repr__': __repr__,
            SINGLETON_INST: None,
            SINGLETON: True,
        },
    )()


def is_singleton(x: Any):
    return hasattr(x, SINGLETON) or hasattr(type(x), SINGLETON)
