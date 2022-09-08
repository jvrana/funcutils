"""Module to house python-specific imports."""
#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
import sys

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
    from typing_extensions import Concatenate
else:
    from typing import ParamSpec
    from typing import Concatenate
import inspect

empty = inspect._empty  # noqa


__all__ = ["ParamSpec", "Concatenate", "empty"]
