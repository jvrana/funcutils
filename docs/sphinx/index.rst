funcutils API
=============

Examples
--------

**Argument Packing**

.. testsetup:: *

    import funcutils
    from funcutils import MutableSignature

    def fn1(a: int, b: float, c: str, d: list) -> tuple:
        return a, b, c, d

    s = MutableSignature(fn1)
    s.pack(('a', 'c', 'd'), position=1)
    fn2 = s.transform(fn1)

New parameter and annotations exist on the new signature

>>> print(str(s.to_signature()))
(b: float, a__c__d: Tuple[int, str, list]) -> tuple

New call signature can be used to transform an existing function to the new call signature:

>>> print(fn2(5.0, (1, 'mystr', [1, 2, 3])))
(1, 5.0, 'mystr', [1, 2, 3])
