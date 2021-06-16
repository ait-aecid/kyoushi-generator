import re

from pathlib import Path
from typing import Optional

import click

from .config import Config
from .plugin import (
    get_generators,
    get_yaml,
)
from .random import SeedStore
from .template import (
    create_environment,
    resolve_generators,
    write_template,
)


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
    yaml = get_yaml(generators)
    env = create_environment(config.jinja)

    context_raw = yaml.load(context_file)
    context = resolve_generators(context_raw, seed_store=SeedStore(seed))

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
                yaml,
                env,
                template,
                dest,
                context,
            )
