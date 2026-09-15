from importlib import import_module

import pytest

from fpathlib.utils import import_optional_dependency


class TestImportOptionalDependency:
    def test_returns_module_when_installed(self):
        module = import_optional_dependency("json")
        assert module is import_module("json")

    def test_raises_module_not_found_error_when_missing(self):
        with pytest.raises(ModuleNotFoundError, match="optional dependency 'not_a_real_package'"):
            import_optional_dependency("not_a_real_package")
