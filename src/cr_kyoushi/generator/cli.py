import re

from pathlib import Path
from typing import Optional

import click

from .config import Config
from .plugin import get_generators
from .random import SeedStore
from .template import (
    create_context_environment,
    create_environment,
    render_template,
    write_template,
)
from .utils import load_config


class Info:
    """An information object to pass data between CLI functions."""

    def __init__(self):  # Note: This object must have an empty constructor.
        """Create a new instance."""


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


@cli.command()
@click.option(
    "--context",
    "-c",
    "context_file",
    type=CliPath(dir_okay=False, readable=True),
    default="context.yml",
)
@click.option(
    "--seed",
    "-s",
    default=None,
    type=click.INT,
    help="Global seed for PRNGs used during context generation",
)
@pass_info
def apply(info: Info, context_file: Path, seed: Optional[int]):
    """Apply and generate the template."""
    config = Config()
    generators = get_generators(config.plugin)
    env = create_environment(config.jinja, generators=generators)
    context_env = create_context_environment(SeedStore(seed), generators)
    context = load_config(render_template(context_env, context_file, {}))

    for template_source in config.templates:
        if template_source.replace is not None:
            (pattern, replace) = template_source.replace
        for template in Path(".").glob(template_source.glob):
            if template_source.replace is not None:
                dest = Path(re.sub(pattern, replace, str(template)))
            else:
                dest = template
            click.echo(f"Rendering {template}")
            write_template(
                env,
                template,
                dest,
                context,
            )
