"""分层规则的自动检查（docs/03-架构与接口.md 第一节）。

不靠人记：谁在 services/ 或 repository/ 里导入了界面库，这里就会失败。
"""
import ast
import importlib
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"


def _py_files(sub: str):
    return sorted((APP / sub).glob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("path", _py_files("services") + _py_files("repository") + _py_files("models"),
                         ids=lambda p: f"{p.parent.name}/{p.name}")
def test_lower_layers_do_not_import_pyside6(path):
    assert "PySide6" not in _imported_modules(path)


@pytest.mark.parametrize("path", _py_files("services") + _py_files("repository"),
                         ids=lambda p: f"{p.parent.name}/{p.name}")
def test_lower_layers_do_not_import_ui(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("app.ui"), f"{path.name} 导入了界面层"


@pytest.mark.parametrize("path", _py_files("services") + _py_files("repository") + _py_files("models"),
                         ids=lambda p: f"{p.parent.name}/{p.name}")
def test_every_module_imports(path):
    """骨架里的每个空壳模块都能被导入，组员拉下来就能在上面写。"""
    module = f"app.{path.parent.name}.{path.stem}"
    importlib.import_module(module)
