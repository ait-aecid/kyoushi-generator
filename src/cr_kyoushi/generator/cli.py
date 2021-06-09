import json
import os
import shutil

from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import click


class Info:
    """An information object to pass data between CLI functions."""

    def __init__(self):  # Note: This object must have an empty constructor.
        """Create a new instance."""
        pass


# pass_info is a decorator for functions that pass 'Info' objects.
#: pylint: disable=invalid-name
pass_info = click.make_pass_decorator(Info, ensure=True)


class CliPath(click.Path):
    """A Click path argument that returns a pathlib Path, not a string"""

    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


@click.group()
@pass_info
def cli(info: Info):
    """Run Cyber Range Kyoushi Generator."""


@cli.command()
@pass_info
def version(info: Info):
    """Get the library version."""
    from .utils import version_info

    click.echo(version_info(cli_info=info))