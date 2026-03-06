"""Generate the code reference pages."""

import os
import sys
from pathlib import Path

import mkdocs_gen_files

PACKAGE_NAME = "senxor"
LAYOUT = "flat"  # "src" or "flat"
INCLUDE_PRIVATE_MODULES = False
EXCLUDE_MODULES = []
INCLUDE_MODULES = []


API_REFERENCE_TEMPLATE = """
## `{module_name}`

::: {module_name}
""".lstrip("\n")


def parse_file_tree(package_name: str, layout: str = "src") -> list[str]:
    """Recursively find all .py files under the package directory.

    Parameters
    ----------
    package_name : str
        The name of the package to search.
    layout : str
        Project layout: "src" or "flat".

    Returns
    -------
    list of str
        List of .py file paths relative to the package root (e.g., ["foo/bar.py", "foo/__init__.py"])

    """
    cwd = Path.cwd()
    src = cwd / "src" if layout == "src" else cwd
    pkg_path = src / package_name.replace(".", os.sep)
    if not pkg_path.exists():
        raise RuntimeError(f"Package path not found: {pkg_path}")
    py_files = [str(p.relative_to(pkg_path)) for p in pkg_path.rglob("*.py")]
    return py_files


def build_module_info_list(py_files: list[str], package_name: str) -> list[dict]:
    modules = []
    for rel_path in py_files:
        parts = rel_path.replace("\\", "/").split("/")
        if parts[-1] == "__init__.py":
            submod = ".".join(parts[:-1]) if len(parts) > 1 else ""
            mod_name = package_name + (f".{submod}" if submod else "")
            is_package = True
        else:
            submod = ".".join(parts)[:-3]  # remove .py
            mod_name = package_name + (f".{submod}" if submod else "")
            is_package = False
        parent = ".".join(mod_name.split(".")[:-1]) if "." in mod_name else None
        modules.append({
            "module_name": mod_name,
            "is_package": is_package,
            "file_path": rel_path,
            "parent": parent,
        })
    return modules


def iter_modules(
    raw_modules: list[dict],
    include_private: bool = False,
    exclude_modules: list[str] = [],
    include_modules: list[str] = [],
) -> list[dict]:
    """Filter the raw module list according to include/exclude/private rules.

    Parameters
    ----------
    raw_modules : list of dict
        Raw module information dictionaries.
    include_private : bool, optional
        Whether to include private modules (default is False).
    exclude_modules : list of str, optional
        List of module names to exclude.
    include_modules : list of str, optional
        List of module names to include with highest priority.

    Returns
    -------
    list of dict
        Filtered module information dictionaries.

    """

    def is_private(name: str) -> bool:
        return name.startswith("_")

    def should_include(mod):
        name = mod["module_name"]
        for inc in include_modules:
            if name == inc or name.startswith(inc + "."):
                return True
        for exc in exclude_modules:
            if name == exc or name.startswith(exc + "."):
                return False
        parts = name.split(".")
        for part in parts:
            if is_private(part):
                return include_private
        return True

    return [m for m in raw_modules if should_include(m)]


def build_doc_file_list(modules: list[dict], output_dir: Path) -> list[dict]:
    """Build the list of documentation files to generate, with template parameters.

    Parameters
    ----------
    modules : list of dict
        List of module information dictionaries.
    output_dir : Path
        The root output directory for API docs (e.g., docs/api).

    Returns
    -------
    list of dict
        Each dict contains: doc_path, module_name, is_package, etc.

    """
    doc_files = []
    for mod in modules:
        mod_name = mod["module_name"]
        subpath = mod_name[len(PACKAGE_NAME) :].lstrip(".")
        parts = subpath.split(".") if subpath else []
        md_dir = output_dir.joinpath(*parts[:-1]) if parts else output_dir
        md_path = md_dir / f"{parts[-1] if parts else PACKAGE_NAME}.md"
        doc_files.append({
            "doc_path": md_path,
            "module_name": mod_name,
            "is_package": mod["is_package"],
        })
    return doc_files


def render_doc_files(doc_files: list[dict], cwd: Path):
    """Render and write documentation files from the doc_files list."""
    for doc in doc_files:
        doc["doc_path"].parent.mkdir(parents=True, exist_ok=True)
        content = API_REFERENCE_TEMPLATE.format(module_name=doc["module_name"])
        with mkdocs_gen_files.open(doc["doc_path"], "w") as f:
            f.write(content)
        print(f"Generated {doc['doc_path'].relative_to(cwd)}")


def main():
    cwd = Path.cwd()
    src = cwd / "src" if LAYOUT == "src" else cwd
    if not src.exists():
        raise RuntimeError(
            f"Can't find the src directory: {src}, check below:\n"
            f"1. The project layout is {LAYOUT}\n"
            f"2. The project name is {PACKAGE_NAME}\n"
            f"3. The src directory is {src}\n"
            f"4. The current working directory is {cwd}\n",
        )
    sys.path.insert(0, str(src))

    py_files = parse_file_tree(PACKAGE_NAME, layout=LAYOUT)
    raw_modules = build_module_info_list(py_files, PACKAGE_NAME)
    modules = iter_modules(
        raw_modules,
        include_private=INCLUDE_PRIVATE_MODULES,
        exclude_modules=EXCLUDE_MODULES,
        include_modules=INCLUDE_MODULES,
    )

    output_dir = cwd / "docs" / "api"
    doc_files = build_doc_file_list(modules, output_dir)
    render_doc_files(doc_files, cwd)


if __name__ == "__main__":
    main()
