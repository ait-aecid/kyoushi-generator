"""
Module containing various util functions and classes.
"""

import json
import re
import sys

from pathlib import Path
from random import Random
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Union,
)

from click import Path as ClickPath
from git import Repo
from git.exc import InvalidGitRepositoryError
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


if TYPE_CHECKING:
    from .cli import Info
else:
    Info = Any


def version_info() -> str:
    """Returns formatted version information about the `cr_kyoushi.generator package`.

    Adapted from
    [Pydantic version.py](https://github.com/samuelcolvin/pydantic/blob/master/pydantic/version.py)

    Returns:
        CLI information about the Cyber Range Kyoushi Generator tool.
    """
    import platform

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


def create_seed() -> int:
    """Create a random integer seed

    Returns:
        An integer seed
    """
    return Random().randint(sys.maxsize * -1, sys.maxsize)


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


def write_config(config: Any, dest: Path):
    """Writes a complex config data type to a file in YAML format.

    Args:
        config: The data to write
        dest: The destination file path
    """
    # need to dump to json first to support the additional types
    # provided by pydantic
    json_str = json.dumps(config, default=pydantic_encoder)

    yaml = YAML(typ="safe")
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False
    yaml.sort_base_mapping_type_on_output = False  # type: ignore
    with open(dest, "w") as config_file:
        obj = json.loads(json_str)
        yaml.dump(obj, config_file)


class TIMSource(ClickPath):
    """Utility click type for TIM sources.

    Allows a TIM source to be either a local file path or a GIT
    repository URI. Common repository link formats e.g.,

     - `https://github.com/acme/foobar.git`
     - `git@github.com:acme/foobar.git`

    will be detected automatically. For less common formats like
    SSH links with a username that is not `git` you will have to prefix `git+`
    to the link.
    """

    name: str = "GIT repo/directory"
    __git_regex: re.Pattern = re.compile(r"(https?|ssh|git)(.+)")
    __git_replace: re.Pattern = re.compile(r"^git\+(.*)$")

    def convert(self, value: str, param, ctx):
        if self.__git_regex.match(value):
            return self.__git_replace.sub(r"\1", value)

        return Path(super().convert(value, param, ctx))


def is_git_repo(path: Union[str, Path]) -> Optional[Repo]:
    """Checks if the directory at the given path is a GIT repository.

    Args:
        path: The path to check

    Returns:
        A Repo object if the directory is a valid repository or None otherwise.
    """
    try:
        return Repo(path)
    except InvalidGitRepositoryError:
        return None
