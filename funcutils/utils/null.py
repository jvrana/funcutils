#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from typing import Any
from typing import Literal

from funcutils.utils.singleton import singleton


@singleton
class Null:
    def __eq__(self, other: Any) -> Literal[False]:
        return False

    def any(self, objs: list) -> bool:
        return any([x is self for x in objs])

    def all(self, objs: list) -> bool:
        return all([x is self for x in objs])


null = Null()
