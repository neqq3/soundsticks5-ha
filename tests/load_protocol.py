"""Load the protocol module without importing Home Assistant integration setup."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
PACKAGE = "soundsticks5_protocol_test"


def load_module(module_name):
    package = ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "soundsticks5")]
    sys.modules[PACKAGE] = package
    for name in ("const", module_name):
        path = ROOT / "custom_components" / "soundsticks5" / f"{name}.py"
        spec = spec_from_file_location(f"{PACKAGE}.{name}", path)
        assert spec and spec.loader
        module = module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules[f"{PACKAGE}.{module_name}"]


def load_protocol():
    return load_module("protocol")
