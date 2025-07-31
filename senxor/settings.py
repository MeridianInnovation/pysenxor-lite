from __future__ import annotations

from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Literal

from senxor._utils.setting import BaseSettings, Profile
from senxor.log import get_logger
from senxor.regmap import Fields

if TYPE_CHECKING:
    from senxor._senxor import Senxor


class SenxorSettings(BaseSettings):
    _logger = get_logger(logger_name="senxor_settings")

    @classmethod
    def _get_local_variables(cls, instance: Senxor) -> dict[str, Any]:
        local_vars = {}
        local_vars["frame_shape"] = instance.get_shape()
        local_vars["address"] = str(instance.address)
        local_vars["type"] = instance.type
        allowed_fields = [name for name in Fields.__name_list__ if name not in Fields.__auto_reset_list__]
        local_vars.update(instance.fields.get_fields(allowed_fields))
        return local_vars

    @classmethod
    def _apply_profile(cls, dst: Senxor, settings: dict[str, Any]) -> None:
        try:
            fields: dict[str, int] = {dst.fields[name].name: value for name, value in settings.items()}
        except KeyError as e:
            raise KeyError("Unsupported field name in settings.") from e
        try:
            dst.fields.set_fields(fields)
        except Exception as e:
            raise ValueError("Can't apply settings to senxor.") from e


def loads(
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

    Examples
    --------
    >>> with open("settings.yaml", "r") as f:
    ...     settings = loads(f, filetype="yaml")

    """
    return SenxorSettings.loads(fp, filetype)


def load(path: str | Path) -> dict[str, Profile]:
    """Load settings from a specified file path.

    Parameters
    ----------
    path : str or Path
        The file path to load settings from. Supports YAML, TOML, and JSON formats.

    Returns
    -------
    dict[str, Profile]
        A dictionary of profiles loaded from the file, where each key is the profile name
        and the value is a `Profile` object.

    Examples
    --------
    >>> settings = load("settings.yaml")
    >>> default_setting = settings["default"]
    >>> default_setting.name
    'default'
    >>> default_setting.settings
    {'foo': 1, 'bar': 2}
    >>> default_setting.when
    'foo > 10 and bar < 20'

    """
    return SenxorSettings.load(path)


def apply(senxor: Senxor, settings: dict[str, Profile] | Profile | str | Path):
    """Apply settings to a Senxor object from either a dictionary of profiles or a file path.

    Parameters
    ----------
    senxor : Senxor
        The Senxor object to which the settings will be applied.
    settings : dict[str, Profile] or Profile or str or Path
        A file path to load settings from, or a dictionary of profiles, or a single profile.

    Examples
    --------
    1. Apply settings from a file path:
    >>> apply(senxor, "settings.yaml")

    2. Apply settings from a dictionary of profiles:
    >>> settings = load("settings.yaml")
    >>> apply(senxor, settings)

    3. Apply a single profile:
    >>> profile = load("settings.yaml")["default"]
    >>> apply(senxor, profile)

    """
    if isinstance(settings, (str, Path)):
        settings = load(settings)
    elif isinstance(settings, Profile):
        settings = {settings.name: settings}

    SenxorSettings.apply_settings(senxor, settings)
