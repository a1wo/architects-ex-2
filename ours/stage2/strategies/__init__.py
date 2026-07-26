"""Strategy registry. Drop a module in this folder that subclasses Strategy
(with a unique `name`) and it shows up in the UI picker automatically.
`base`, `llm` and `retrieval` are infrastructure, not strategies.
"""

import importlib
import pkgutil

from .base import Citation, Context, Strategy, StrategyResult  # noqa: F401

_INFRA = {"base", "llm", "retrieval"}

STRATEGIES: dict[str, Strategy] = {}
for _m in pkgutil.iter_modules(__path__):
    if _m.name in _INFRA or _m.name.startswith("_"):
        continue
    _mod = importlib.import_module(f"{__name__}.{_m.name}")
    for _obj in vars(_mod).values():
        if (isinstance(_obj, type) and issubclass(_obj, Strategy)
                and _obj is not Strategy):
            STRATEGIES[_obj.name] = _obj()
