"""A settings manager utility."""

from __future__ import annotations

import ast
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, ClassVar, Literal

import yaml

from senxor.log import get_logger

if sys.version_info >= (3, 10):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from senxor import Senxor


class ExprEvaluator:
    # Allowed AST nodes
    ALLOWED_NODES: ClassVar[set[type[ast.AST]]] = {
        ast.Expression,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Name,
        ast.Constant,
        ast.Load,
        ast.List,
        ast.Tuple,
        ast.Set,
    }

    @staticmethod
    def parse_and_validate_expr(expr: str) -> tuple[ast.Expression, list[str]]:
        """Validate a condition expression and return the list of variables used in the expression."""
        variables = set()
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if type(node) not in ExprEvaluator.ALLOWED_NODES:
                raise ValueError(f"Disallowed syntax: {type(node).__name__}")
            if isinstance(node, ast.Name):
                variables.add(node.id)

        return tree, list(variables)

    @staticmethod
    def eval_expr(tree: ast.Expression, variables: dict[str, Any]) -> bool:
        """Parse and execute boolean conditions.

        This function does not check the safety of the expression. Use `parse_and_validate_expr` first.
        """
        code = compile(tree, "<expr>", "eval")
        try:
            res = bool(eval(code, {}, variables))  # noqa: S307
        except Exception as e:
            raise ValueError(f"Error evaluating condition: {e}") from e
        return res


@dataclass
class Profile:
    name: str
    settings: dict[str, Any]
    desc: str | None = None
    when: str | None = None

    class When:
        def __init__(self, expr: str):
            self.expr = expr
            try:
                tree, variables = ExprEvaluator.parse_and_validate_expr(expr)
            except Exception as e:
                raise ValueError(f"Invalid expression: {expr}") from e
            self.tree = tree
            self.variables = variables

        def eval(self, locals: dict[str, Any]) -> bool:
            """Evaluate the expression with the given local variables."""
            return ExprEvaluator.eval_expr(self.tree, locals)

    def __post_init__(self):
        if self.when is not None:
            self.when_expr = Profile.When(self.when)
        else:
            self.when_expr = None

        self._logger = get_logger().bind(name=self.name, expr=self.when)

    def check_when(self, variables: dict[str, Any]) -> bool:
        if self.when_expr is None:
            return True
        else:
            locals = {var: variables[var] for var in self.when_expr.variables}
            self._logger.debug("eval_when_expression", locals=locals)
            return self.when_expr.eval(locals)


class BaseSettings(ABC):
    """Settings manager base class.

    Inherit this class to create a settings manager.

    There are two abstract methods need to be implemented:
    - `_get_local_variables`: Return a dictionary of local variables for the condition evaluation.
    - `_apply_profile`: Apply a profile to the destination object.

    Settings can be loaded from a file, or a dictionary.

    The dictionary should follow the following structure:
    {
        "profiles": [
            {
                "name": "profile_name",
                "desc": "profile_description",
                "when": "condition_expression",
                "settings": {
                    "setting_name": "setting_value",
                    ...
                }
            },
            ...
        ]
    }

    If loaded from a file, the file will be parsed to above structure.

    For yaml, it looks like:

    ```yaml
    profiles:
      - name: "profile_name"
        desc: "profile_description"
        when: "condition_expression"
        settings:
          setting_name: "setting_value"
          ...
    ```

    For toml, it looks like:

    ```toml
    [[profiles]]
    name = "profile_name"
    desc = "profile_description"
    when = "condition_expression"
    [profiles.settings]
    setting_name = "setting_value"
    ...
    ```

    For json, it looks like:

    ```json
    {
        "profiles": [
            {
                "name": "profile_name",
                "desc": "profile_description",
                "when": "condition_expression",
                "settings": {
                    "setting_name": "setting_value",
                    ...
                }
            },
            ...
        ]
    ```

    The `when` field is optional. It should be a string of python expression. e.g. `foo > 10 and bar < 20`.

    Setting Manager will evaluate the `when` expression with the local variables provided by `_get_local_variables` and
    skip the profile if the result is false.
    """

    _logger = get_logger()

    @classmethod
    @abstractmethod
    def _get_local_variables(cls, instance: Any) -> dict[str, Any]:
        """Return a dictionary of local variables for the condition evaluation."""
        ...

    @classmethod
    @abstractmethod
    def _apply_profile(cls, obj: Any, settings: dict[str, Any]) -> None:
        """Apply a profile to a destination object."""
        ...

    @staticmethod
    def _load_file(path: str | Path) -> dict[str, Any]:
        """Load settings from a file, support yaml, toml, json."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"Path is a directory: {path}")
        if path.suffix == ".yaml":
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".toml":
            with path.open("rb") as f:
                data = tomllib.load(f)
        elif path.suffix == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        return data

    @staticmethod
    def _load_profiles(data: dict[str, Any]) -> dict[str, Profile]:
        """Load profiles from a dictionary."""
        profiles_list = data.get("profiles")
        if profiles_list is None:
            raise ValueError("`profiles` key not found.")
        if not isinstance(profiles_list, list):
            raise ValueError("`profiles` must be a list of `profile` dict.")
        profiles = {}
        for profile_dict in profiles_list:
            if not isinstance(profile_dict, dict):
                raise ValueError("`profile` must be a dict.")
            profile = Profile(**profile_dict)
            profiles[profile.name] = profile
        return profiles

    @classmethod
    def load(cls, path: str | Path):
        """Load settings from a file, support yaml, toml, json."""
        data = cls._load_file(path)
        cls._logger.info("load_settings_from_file", path=path)
        return cls.load_from_dict(data)

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]):
        """Load settings from a dictionary."""
        try:
            profiles = BaseSettings._load_profiles(data)
            cls._logger.info("load_settings_success", profiles=list(profiles.keys()))
        except Exception as e:
            cls._logger.error("load_settings_failed", error=e)
            raise
        return profiles

    @classmethod
    def loads(
        cls,
        fp: str | bytes | IO[str] | IO[bytes],
        filetype: Literal["yaml", "toml", "json"] = "yaml",
    ) -> dict[str, Profile]:
        """Load settings from a file-like object or string, specifying the file type.

        Parameters
        ----------
        fp : file-like object or str or bytes
            A file-like object with a `.read()` method or a string/bytes containing the settings data.
        filetype : Literal["yaml", "toml", "json"], optional
            The file type to parse ('yaml', 'toml', or 'json'). Default is 'yaml'.

        Returns
        -------
        dict[str, Profile]
            A dictionary of profiles loaded from the input, where each key is the profile name
            and the value is a `Profile` object.

        """
        if hasattr(fp, "read"):
            content = fp.read()  # type: ignore[reportAttributeAccessIssue]
        elif isinstance(fp, (bytes, str)):
            content = fp
        else:
            raise TypeError("Input must be a file-like object or a string or bytes.")

        if filetype == "yaml":
            data = yaml.safe_load(content)
        elif filetype == "toml":
            if isinstance(content, str):
                data = tomllib.loads(content)
            elif isinstance(content, bytes):
                data = tomllib.loads(content.decode("utf-8"))
            else:
                raise TypeError("TOML content must be str or bytes.")
        elif filetype == "json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported file type: {filetype}")

        return cls.load_from_dict(data)

    @classmethod
    def apply_settings(
        cls,
        obj: Any,
        profiles: dict[str, Profile],
    ) -> None:
        """Apply settings to a destination object."""
        for profile in profiles.values():
            local_vars = cls._get_local_variables(obj)
            if profile.check_when(local_vars):
                cls._apply_profile(obj, profile.settings)
                cls._logger.info("apply_profile_success", profile=profile.name, settings=profile.settings)
            else:
                cls._logger.info("skip_profile", profile=profile.name)
