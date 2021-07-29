import shutil

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
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
    Directory,
    File,
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
    write_config,
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
def cli():
    """Run Cyber Range Kyoushi Generator."""


@cli.command()
def version():
    """Get the library version."""
    from .utils import version_info

    click.echo(version_info())


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
) -> Tuple[Dict[str, Any], List[Union[File, Directory]]]:
    seed_store = SeedStore(seed)
    # env used for rendering the context variables
    context_env = create_context_environment(
        seed_store, generators=generators, template_dirs=dest
    )
    # env used for rendering the template object configuration
    object_config_env = create_template_object_environment(template_dirs=dest)
    # env used for templating
    render_env = create_environment(
        seed_store, jinja_config, template_dirs=dest, generators=generators
    )

    # instantiate the TIM context model to a TSM context
    context = load_config(render_template(context_env, context_file, {}))

    # render object config -> load as python data types -> validate and transform to pydantic model list
    object_config = validate_object_list(
        load_config(render_template(object_config_env, object_config_file, context))
    )

    (delete_dirs, delete_files) = render_tim(
        render_env,
        object_config,
        Path("."),
        dest,
        context,
    )

    # remove template files
    while delete_files:
        f = dest.joinpath(delete_files.pop())
        dest.joinpath(f).unlink()

    # remove template directories
    while delete_dirs:
        d = dest.joinpath(delete_dirs.pop())
        shutil.rmtree(dest.joinpath(d))

    return (context, object_config)


def write_tsm_configs(
    model_dir: Path,
    config: Config,
    context: Dict[str, Any],
    object_config: List[Union[File, Directory]],
):
    write_config(config.dict(), model_dir.joinpath("config.yml"))
    write_config(context, model_dir.joinpath("context.yml"))
    write_config(object_config, model_dir.joinpath("templates.yml"))


@cli.command()
@click.option(
    "--model",
    "-m",
    "model_dir",
    type=CliPath(file_okay=False, readable=True),
    default=None,
    help="The model directory for the TIM that is to be instantiated",
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
def apply(
    model_dir: Optional[Path],
    seed: Optional[int],
    src: Union[Path, str],
    dest: Path,
):
    """Apply and generate the template."""

    # setup default relative paths
    if model_dir is None:
        model_dir = Path("model")

    model_dir = dest.joinpath(model_dir)

    # config file paths
    cli_config = model_dir.joinpath("config.yml")
    context_file = model_dir.joinpath("context.yml.j2")
    file_config = model_dir.joinpath("templates.yml.j2")

    repo: Repo = setup_repository(src, dest)

    if cli_config.exists():
        with open(cli_config, "r") as f:
            config = Config(**load_config(f.read()))
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
    (context, object_config) = setup_tsm(
        config.seed,
        config.jinja,
        dest,
        generators,
        context_file.relative_to(dest),
        file_config.relative_to(dest),
    )

    write_tsm_configs(model_dir, config, context, object_config)

    # placeholder for adding commit code later
    repo.index.add("*")
    repo.index.commit(f"Generate TSM with seed: '{config.seed}'")
    click.echo(f"Created TSM in {dest}")
    click.echo(
        "You can now change to the directory and push TSM to a new GIT repository."
    )
