#  Copyright (c) 2022 Justin Vrana. All Rights Reserved.
#  You may use, distribute, and modify this code under the terms of the MIT license.
from inspect import Parameter
from inspect import Signature
from typing import Any
from typing import Callable
from typing import List
from typing import Union


SignatureLike = Union[Callable[..., Any], Signature, List[Parameter]]
