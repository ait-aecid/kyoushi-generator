import json

from typing import (
    TYPE_CHECKING,
    Any,
)

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


if TYPE_CHECKING:
    from .cli import Info
else:
    Info = Any


def version_info(cli_info: Info) -> str:
    """Returns formatted version information about the `cr_kyoushi.generator package`.

    Adapted from
    [Pydantic version.py](https://github.com/samuelcolvin/pydantic/blob/master/pydantic/version.py)
    """
    import platform
    import sys

    from pathlib import Path

    from . import __version__

    info = {
        "cr_kyoushi.testbed version": __version__,
        "install path": Path(__file__).resolve().parent,
        "python version": sys.version,
        "platform": platform.platform(),
    }
    return "\n".join(
        "{:>30} {}".format(k + ":", str(v).replace("\n", " ")) for k, v in info.items()
    )


def load_config(config: str) -> Any:
    """Loads either a YAML or JSON config string.

    Non string arguments are returned as is.

    Args:
        config: The config string

    Returns:
        The loaded config as python data types
    """
    if isinstance(config, str):
        yaml = YAML(typ="safe")
        try:
            return yaml.load(config)
        except YAMLError:
            return json.loads(config)
    else:
        return config
