from typing import Any
from typing import Literal

from funcutils.utils.singleton import is_singleton
from funcutils.utils.singleton import singleton


def test_singleton_wrapper():
    class Foo:
        ...

    assert Foo() is not Foo()

    Foo2 = singleton(Foo)

    assert Foo2 is Foo2
    assert Foo2() is Foo2()
    assert Foo2 is Foo2()
    assert Foo2() is Foo2


def test_singleton_factory():
    Foo = singleton("Foo")
    assert id(Foo()) == id(Foo())
    assert id(Foo) == id(Foo())
    assert id(Foo) == id(Foo)
    assert id(Foo()) == id(Foo)
    assert is_singleton(Foo)
    print(Foo)


def test_intended_usage():
    """The preferred usage it so create a class and instance to initialize the
    singleton.

    This is only to help the IDE and typcheckers understand how to use
    the singleton.
    """

    @singleton
    class MyNull:
        def __eq__(self, other: Any) -> Literal[False]:
            """Always return False."""
            return False

    mynull = MyNull()

    def fn(a: MyNull):
        return a

    # how we use Null in practice is of no consequence.
    # preferably, we use `null` so that typecheckers do not complain
    assert fn(mynull) is fn(MyNull)
    assert fn(mynull) is fn(MyNull())

    # nulls never equal anything
    assert not fn(mynull) == fn(MyNull)
    assert not fn(mynull) == fn(MyNull())
