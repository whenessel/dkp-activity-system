import importlib
import pkgutil
import typing as t


def is_cog_module(module: t.Any) -> bool:
    attr = getattr(module, "setup", None)
    return True if attr else False


def is_package(module: t.Any) -> bool:
    mod_name = module.__name__
    parent_name = module.__spec__.parent
    return mod_name == parent_name


def find_submodules(module: t.Any) -> t.List[str]:
    sub_modules_list = []
    try:
        sub_modules = pkgutil.iter_modules(module.__path__)
        for importer, sub_mod_name, is_pkg in sub_modules:
            sub_modules_list.append(sub_mod_name)
    except AttributeError:
        ...
    return sub_modules_list


def safety_import_module(module_name: str) -> t.Optional[t.Any]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    return module


def find_cogs(list_modules: t.List[str]) -> list:
    cogs_list = []

    for mod_name in list_modules:
        module = safety_import_module(mod_name)

        _is_cog_module = is_cog_module(module)
        # _is_package = is_package(module)

        if _is_cog_module:
            cogs_list.append(mod_name)
            continue

        if not _is_cog_module:
            sub_mod_name = f"{mod_name}.cogs"
            sub_module = safety_import_module(sub_mod_name)
            if sub_module:
                mod_name = sub_mod_name
                module = sub_module

        _is_cog_module = is_cog_module(module)

        if _is_cog_module:
            cogs_list.append(mod_name)
            continue

        for sub_mod_name in find_submodules(module):
            sub_mod_name = f"{mod_name}.{sub_mod_name}"
            sub_module = safety_import_module(sub_mod_name)

            _is_cog_module = is_cog_module(sub_module)

            if _is_cog_module:
                cogs_list.append(sub_mod_name)

    return cogs_list


def search_cogs(list_modules: t.List[str]) -> list:
    cogs_list = []
    for m in list_modules:
        cogs_module_name = m + ".cogs"
        cogs_module = importlib.import_module(cogs_module_name)
        try:
            for importer, modname, is_pkg in pkgutil.iter_modules(cogs_module.__path__):
                sub_cogs_module_name = f"{cogs_module_name}.{modname}"
                sub_cogs_module = importlib.import_module(sub_cogs_module_name)
                if getattr(sub_cogs_module, "setup", False):
                    continue
                cogs_list.append(sub_cogs_module_name)

        except (ImportError, AttributeError):
            ...

    return cogs_list
