"""
The CLI module
"""

import re
import shutil

from json import JSONDecodeError
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import click

from git import Repo
from pydantic import (
    parse_obj_as,
    parse_raw_as,
)

from .config import (
    Config,
    InputDict,
    InputVarsDict,
    JinjaConfig,
    MissingInput,
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

    def convert(self, value: str, param: str, ctx: click.Context):
        """Convert str path into pathlib.Path

        Args:
            value: The string path
            param: The CLI parameter
            ctx: The click context

        Returns:
            The parameter converted to a pathlib.Path
        """
        return Path(super().convert(value, param, ctx))


def validate_var(
    ctx: click.Context, param: str, value: Sequence[str]
) -> Dict[str, str]:
    """Validate and convert CLI input vars.

    Convert CLI input vars of the form
    `<name>=<value>` into a dict `<name> => <value>`.

    Args:
        ctx: The click context
        param: The click parameter
        value: Sequence of CLI input variables

    Raises:
        click.BadParameter: If one or more input vars have an invalid name

    Returns:
        Input variable dict
    """
    input_vars: Dict[str, str] = {}
    errors: List[str] = []
    for var in value:
        match = re.match(r"^([\w\d-]*)=(.*)", var)
        if match:
            input_vars[match.group(1)] = match.group(2)
        else:
            errors.append(var)

    if len(errors) > 0:
        raise click.BadParameter(f"Invalid var definitions: {errors}")

    return input_vars


def validate_var_file(
    ctx: click.Context, param: str, value: Sequence[str]
) -> InputVarsDict:
    """Converts CLI input var files into an input var dict.

    This function loads all given input var files and combines
    them in a single input var dict.

    Args:
        ctx: The click context
        param: The click parameter
        value: The CLI input var files

    Returns:
        The resulting input var dict.
    """
    input_vars: InputVarsDict = {}
    for file_path in value:
        with open(file_path, "r") as var_file:
            var_file_raw = var_file.read()
            if len(var_file_raw.strip()) > 0:
                var_file_content: Dict[str, str] = load_config(var_file_raw)
                input_vars.update(parse_obj_as(InputVarsDict, var_file_content))

    return input_vars


def convert_input_vars(
    inputs_config: InputDict, input_vars: InputVarsDict
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Convert raw input var dicts to configured inputs.

    This function uses the given inputs configuration
    to convert raw inputs to the defined python types.
    It will also return a list of missing required inputs
    and given inputs which are not part of the configuration.

    Args:
        inputs_config: The inputs configuration
        input_vars: Input var dict with raw CLI inputs

    Returns:
        Tuple of the form
        (parsed inputs, missing required inputs, unused given inputs)
    """
    inputs: Dict[str, Any] = {}
    missing_inputs: List[str] = []

    # load the defined input variables
    for _id, _input in inputs_config.items():
        if _id in input_vars:
            _input.value = input_vars.pop(_id)

        if not isinstance(_input.value, MissingInput):
            # ignoring typing for parse function since annotation only accepts type hint objects
            # but code also allows type hint strings
            try:
                inputs[_id] = parse_raw_as(_input.model, _input.value)  # type: ignore
            except JSONDecodeError:
                # for convenience we allow to pass strings as is
                # without requiring sourunding double quotes
                inputs[_id] = parse_obj_as(_input.model, _input.value)  # type: ignore
        elif _input.required:
            missing_inputs.append(_id)

    unused_inputs: List[str] = list(input_vars.keys())

    return (inputs, missing_inputs, unused_inputs)


@click.group()
def cli():
    """Run Cyber Range Kyoushi Generator."""


@cli.command()
def version():
    """Get the library version."""
    from .utils import version_info

    click.echo(version_info())


def setup_repository(src: Union[Path, str], dest: Path) -> Repo:
    """Copies a TIM repository to prepare for the creation of a TSM.

    Args:
        src: The TIM source (can be local path or GIT url)
        dest: The local path to create the TSM in

    Returns:
        The GIT repo object for the created TSM path
    """
    repo: Optional[Repo]

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
    inputs: Dict[str, Any],
    dest: Path,
    generators: List[Generator],
    context_file: Path,
    object_config_file: Path,
) -> Tuple[Dict[str, Any], List[Union[File, Directory]]]:
    """Convert TIM into a TSM by rendering all TIM templates.

    Args:
        seed: The initial TSM seed to use
        jinja_config: The TIM jinja2 configuration
        inputs: The CLI input variables
        dest: The TSM directory
        generators: The available random generators
        context_file: The TIM context template file path
        object_config_file: The TIM template object file path

    Returns:
        The rendered TSM context and template object config as tuple.
        (context, object config)
    """
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
    context = load_config(
        render_template(context_env, context_file, {"inputs": inputs})
    )

    # render object config -> load as python data types -> validate and transform to pydantic model list
    object_config = validate_object_list(
        load_config(
            render_template(
                object_config_env,
                object_config_file,
                {"context": context, "inputs": inputs},
            )
        )
    )

    (delete_dirs, delete_files) = render_tim(
        render_env,
        object_config,
        Path("."),
        dest,
        inputs,
        context,
    )

    # remove template files
    while delete_files:
        f = dest.joinpath(delete_files.pop())
        f.unlink()

    # remove template directories
    while delete_dirs:
        d = dest.joinpath(delete_dirs.pop())
        shutil.rmtree(d)

    return (context, object_config)


def write_tsm_configs(
    model_dir: Path,
    config: Config,
    context: Dict[str, Any],
    object_config: List[Union[File, Directory]],
):
    """Write the rendered TSM config files.

    Args:
        model_dir: The model directory path
        config: The TSM config (contains the used seed and CLI inputs)
        context: The rendered TSM context
        object_config: The rendered template object config
    """
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
@click.option("--var", multiple=True, callback=validate_var)
@click.option(
    "--var-file",
    multiple=True,
    type=CliPath(exists=True, file_okay=True, dir_okay=False),
    callback=validate_var_file,
)
@click.argument("src", type=TIMSource(exists=True, file_okay=False))
@click.argument("dest", type=CliPath(exists=False, file_okay=False))
def apply(
    model_dir: Optional[Path],
    seed: Optional[int],
    var: InputVarsDict,
    var_file: InputVarsDict,
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

    input_vars = var_file.copy()
    input_vars.update(var)

    (inputs, missing_inputs, unused_inputs) = convert_input_vars(
        config.inputs, input_vars
    )

    if len(missing_inputs) > 0:
        click.echo(f"Missing required input variables: {missing_inputs}", err=True)
        exit(2)

    if len(unused_inputs) > 0:
        click.secho(f"Unused input variables: {unused_inputs}", fg="yellow")

    generators = get_generators(config.plugin)

    # render context config template and load data
    (context, object_config) = setup_tsm(
        config.seed,
        config.jinja,
        inputs,
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


@cli.command()
@click.option(
    "--model",
    "-m",
    "model_dir",
    type=CliPath(file_okay=False, readable=True),
    default=None,
    help="The model directory for the TIM that is to be instantiated",
)
@click.argument("src", type=TIMSource(exists=True, file_okay=False))
def inspect(model_dir: Optional[Path], src: Union[Path, str]):
    # setup default relative paths
    if model_dir is None:
        model_dir = Path("model")

    if isinstance(src, str):
        src = Path(src)

    model_dir = src.joinpath(model_dir)

    # config file paths
    cli_config = model_dir.joinpath("config.yml")

    if cli_config.exists():
        with open(cli_config, "r") as f:
            config = Config(**load_config(f.read()))
    else:
        config = Config()

    click.secho(f"Input variables for {str(src)}:", bold=True, underline=True)

    for _id, _input in config.inputs.items():
        click.secho(f"\t{_id}", nl=False, bold=True)
        if _input.required:
            click.secho(" (required)", fg="bright_magenta", nl=False)
        else:
            click.secho(" (optional)", fg="bright_green", nl=False)
        click.secho(f" {_input.model}", fg="cyan", nl=False)
        click.secho(":", bold=True)
        if not isinstance(_input.value, MissingInput):
            click.echo("\t  default: ", nl=False)
            click.echo(_input.value)
        if _input.description is not None:
            for _line in _input.description.splitlines():
                click.secho(f"\t  {_line}", dim=True)
        click.echo()
