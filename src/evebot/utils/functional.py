from __future__ import annotations

import importlib
import pkgutil
from typing import List


def search_cogs(list_modules: List[str]) -> list:
    cogs_list = []
    for m in list_modules:
        cogs_module_name = m + ".cogs"
        try:
            cogs_module = importlib.import_module(cogs_module_name)
            for importer, modname, ispkg in pkgutil.iter_modules(cogs_module.__path__):
                cogs_list.append(f"{cogs_module_name}.{modname}")
        except ImportError:
            pass
    return cogs_list
