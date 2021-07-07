import shutil

from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)

import click

from git import Repo

from .config import (
    Config,
    JinjaConfig,
)
from .plugin import (
    Generator,
    get_generators,
)
from .random import SeedStore
from .template import (
    create_context_environment,
    create_environment,
    create_template_object_environment,
    render_template,
    render_tim,
    validate_object_list,
)
from .utils import (
    TIMSource,
    create_seed,
    is_git_repo,
    load_config,
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


def setup_repository(src: Union[Path, str], dest: Path) -> Repo:
    repo: Repo

    # check if source is git repo or local path and copy it to TSM destination
    if isinstance(src, Path):
        shutil.copytree(src, dest)
        repo = is_git_repo(dest)
        if repo is None:
            repo = Repo.init(dest, mkdir=False)
        else:
            repo.delete_remote(repo.remote())
    else:
        repo = Repo.clone_from(src, str(dest.absolute()))
        repo.delete_remote(repo.remote())

    return repo


def setup_tsm(
    seed: int,
    jinja_config: JinjaConfig,
    dest: Path,
    generators: List[Generator],
    context_file: Path,
    object_config_file: Path,
):
    # env used for rendering the context variables
    context_env = create_context_environment(
        SeedStore(seed), generators=generators, template_dirs=dest
    )
    # env used for rendering the template object configuration
    object_config_env = create_template_object_environment(template_dirs=dest)
    # env used for templating
    render_env = create_environment(
        jinja_config, template_dirs=dest, generators=generators
    )

    # instantiate the TIM context model to a TSM context
    context = load_config(render_template(context_env, context_file, {}))

    # render object config -> load as python data types -> validate and transform to pydantic model list
    object_config = validate_object_list(
        load_config(render_template(object_config_env, object_config_file, context))
    )

    print(f"Template object list: {object_config}")
    click.confirm("Next step")
    render_tim(
        render_env,
        object_config,
        Path("."),
        Path("."),
        context,
    )


@cli.command()
@click.option(
    "--config",
    "-c",
    "cli_config",
    type=CliPath(dir_okay=False, readable=True),
    default=None,
    help="The generator configuration file (defaults to <src>/model/config.yml)",
)
@click.option(
    "--context",
    "-ctx",
    "context_file",
    type=CliPath(dir_okay=False, readable=True),
    default=None,
    help="The TIM context configuration file (defaults to <src>/model/context.yml.j2",
)
@click.option(
    "--file-config",
    "-f",
    "file_config",
    type=CliPath(dir_okay=False, readable=True),
    default=None,
    help="The TIM template objects configuration file (defaults to <src>/model/templates.yml.j2",
)
@click.option(
    "--seed",
    "-s",
    default=None,
    type=click.INT,
    help="Global seed for PRNGs used during context generation",
)
@click.argument("src", type=TIMSource(exists=True, file_okay=False))
@click.argument("dest", type=CliPath(exists=False, file_okay=False))
@pass_info
def apply(
    info: Info,
    cli_config: Path,
    context_file: Path,
    file_config: Path,
    seed: Optional[int],
    src: Union[Path, str],
    dest: Path,
):
    """Apply and generate the template."""

    # setup default relative paths
    if cli_config is None:
        cli_config = Path("model/config.yml")
    if context_file is None:
        context_file = Path("model/context.yml.j2")
    if file_config is None:
        file_config = Path("model/templates.yml.j2")

    repo: Repo = setup_repository(src, dest)

    cli_config = dest.joinpath(cli_config)
    if cli_config.exists():
        with open(cli_config, "r") as f:
            config = Config(**load_config(f.read()))
        # config = Config.parse_file(cli_config)
    else:
        config = Config()

    # setup the seed
    if seed is None:
        if config.seed is None:
            config.seed = create_seed()
    else:
        config.seed = seed

    generators = get_generators(config.plugin)

    # render context config template and load data
    setup_tsm(config.seed, config.jinja, dest, generators, context_file, file_config)

    # placeholder for adding commit code later
    print(repo)
