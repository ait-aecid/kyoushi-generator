import importlib.resources as pkg_resources
import io
import json
import os
import shutil

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Dict,
    List,
    Optional,
    Sequence,
    Text,
    Union,
)


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
