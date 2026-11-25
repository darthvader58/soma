"""Build the public signature catalog from source without importing optional extras."""

import argparse
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/reference/api-catalog.mdx"
MODULES = {
    "soma": ("plan_delivery",),
    "soma.engine": ("plan_run",),
    "soma.geometry": None,
    "soma.time": None,
    "soma.time.spice": ("utc_to_et",),
    "soma.terrain": None,
    "soma.illumination": None,
    "soma.power": None,
    "soma.links": None,
    "soma.schedule": None,
    "soma.validation": (
        "ScenarioValidationError", "load_json", "validate_document", "validate_documents",
        "validate_scenario", "load_scenario", "scenario_sha256", "data_volume_bytes",
        "schema_registry", "resource_directory",
    ),
    "soma.exports": (
        "json_bytes", "summary", "display_payload", "explanation", "create_run_package",
    ),
    "soma.exports.display": ("display_data", "renderer_registration"),
    "soma.research": None,
    "soma.research.catalog": ("site_catalog", "resolve_site"),
}


def module_path(module):
    path = ROOT.joinpath(*module.split("."))
    return path / "__init__.py" if path.is_dir() else path.with_suffix(".py")


def definition(module, name):
    path = module_path(module)
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return path, node
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    if node.level:
                        package = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
                        target = ".".join(package[:len(package) - node.level + 1])
                        if node.module:
                            target += "." + node.module
                    else:
                        target = node.module
                    return definition(target, alias.name)
    raise ValueError(f"Missing public definition: {module}.{name}")


def signature(node, name=None, method=False):
    args = ast.unparse(node.args)
    if method:
        args = args.removeprefix("self, ").removeprefix("cls, ")
        if args in ("self", "cls"):
            args = ""
    result = f"{name or node.name}({args})"
    if node.returns:
        result += " -> " + ast.unparse(node.returns)
    return result


def class_lines(node):
    constructor = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
    if constructor:
        lines = [signature(constructor, node.name, method=True)]
    elif any((isinstance(d, ast.Name) and d.id == "dataclass") or
             (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
             for d in node.decorator_list):
        fields = []
        for field in node.body:
            if isinstance(field, ast.AnnAssign):
                value = f"{field.target.id}: {ast.unparse(field.annotation)}"
                if field.value is not None:
                    value += " = " + ast.unparse(field.value)
                fields.append(value)
        lines = [node.name + "(" + ", ".join(fields) + ")"]
    else:
        lines = ["class " + node.name + ("(" + ", ".join(ast.unparse(base) for base in node.bases) + ")" if node.bases else "")]
    for child in node.body:
        if isinstance(child, ast.FunctionDef) and not child.name.startswith("_"):
            lines.append(signature(child, f"{node.name}.{child.name}", method=True))
    return lines


def render():
    lines = ["---", "title: Public API signatures", "description: Exact source-derived signatures for the documented Python interfaces.", "---", "",
             "This catalog is generated from the repository source. The module guides explain parameters, units, returned records, exceptions and scientific limits. Dictionary contents are specified in those guides and the JSON schemas; a Python signature alone does not define a complete scenario.", "",
             "Only declared package exports and the explicitly documented engine, validation and export interfaces appear here. Internal acquisition, renderer and service helpers are outside this catalog. Optional dependencies are listed in [installation](/getting-started/installation).", "",
             "Maintainers regenerate this page with `python docs/scripts/generate_api_catalog.py` and check for drift with `python docs/scripts/generate_api_catalog.py --check`.", ""]
    for module, names in MODULES.items():
        if names is None:
            tree = ast.parse(module_path(module).read_text())
            names = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets))
        lines += [f"## `{module}`", ""]
        for name in names:
            path, node = definition(module, name)
            source = path.relative_to(ROOT).as_posix()
            lines += [f"### `{name}`", "", "```python"]
            lines += class_lines(node) if isinstance(node, ast.ClassDef) else [signature(node)]
            lines += ["```", "", f"[Source](https://github.com/darthvader58/soma/blob/main/{source}#L{node.lineno})", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit("Public API catalog is stale; regenerate it from source.")
        print("Public API catalog matches source.")
    else:
        OUTPUT.write_text(rendered)
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
