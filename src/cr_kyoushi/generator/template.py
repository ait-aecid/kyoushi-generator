"""
Module for TIM templating logic and classes.
"""

import shutil
import sys

from collections import deque
from pathlib import Path
from typing import (
    Any,
    Deque,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Text,
    Tuple,
    Union,
)

from jinja2 import (
    FileSystemLoader,
    StrictUndefined,
    Undefined,
)
from jinja2.nativetypes import NativeEnvironment
from pydantic import (
    BaseModel,
    Field,
    parse_obj_as,
)
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML

from .config import JinjaConfig
from .plugin import Generator
from .random import SeedStore


if sys.version_info >= (3, 8):
    from typing import (
        Annotated,
        Literal,
    )
else:
    # need to use backport for python < 3.8
    from typing_extensions import (
        Annotated,
        Literal,
    )


def _add_env_options(env: NativeEnvironment):
    # use pydantic encoder as default for dumps to add support for more types
    env.policies["json.dumps_kwargs"] = {"sort_keys": True, "default": pydantic_encoder}


def create_template_object_environment(
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./")
) -> NativeEnvironment:
    """Creates the Jinja2 context for rendering the `templates.yml.j2` configuration.

    Args:
        template_dirs: The Jinja2 template directory.

    Returns:
        Jinja2 NativeEnvironment for rendering the templates configuration.
    """
    env = NativeEnvironment(
        loader=FileSystemLoader(template_dirs),
        undefined=StrictUndefined,
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
    )
    _add_env_options(env)
    return env


def _env_add_generators(
    env: NativeEnvironment,
    seed_store: SeedStore,
    generators: List[Generator],
):
    for gen in generators:
        gen_instance = gen.create(seed_store)
        env.globals.update({gen.name: gen_instance})


def create_context_environment(
    seed_store: SeedStore,
    generators: List[Generator] = [],
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./"),
) -> NativeEnvironment:
    """Creates the Jinja2 context for rendering the TIM context configuration.

    Args:
        seed_store: The seed store to use for generating PRNG seeds.
        generators: The random data generators to make available in the Jinja2 context
        template_dirs: The Jinja2 template directory.

    Returns:
        Jinja2 NativeEnvironment for rendering the TIM context.
    """
    env = create_template_object_environment(template_dirs)
    _env_add_generators(env, seed_store, generators)

    return env


def create_environment(
    seed_store: SeedStore,
    config: JinjaConfig,
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./"),
    generators: List[Generator] = [],
) -> NativeEnvironment:
    """Creates the Jinja2 context for rendering the TIM templates.

    Args:
        config: The Jinja2 configuration.
        template_dirs: The Jinja2 template directory.
        generators: The random data generators to make available in the Jinja2 context

    Returns:
        Jinja2 NativeEnvironment for rendering the TIM.
    """
    env = NativeEnvironment(
        loader=FileSystemLoader(template_dirs),
        block_start_string=config.block_start,
        block_end_string=config.block_end,
        variable_start_string=config.variable_start,
        variable_end_string=config.variable_end,
        comment_start_string=config.comment_start,
        comment_end_string=config.comment_end,
        line_statement_prefix=config.line_statement,
        line_comment_prefix=config.line_comment,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
    )
    _add_env_options(env)
    _env_add_generators(env, seed_store, generators)

    return env


def render_template(
    env: NativeEnvironment,
    template: Union[Text, Path],
    context: Any,
) -> Any:
    """Utility function for rendering Jinja2 text or file templates.

    Args:
        env: The Jinja2 environment to use for rendering
        template: The template string or file to render
        context: The context variables to use for rendering

    Returns:
        The rendered template string or data structure
    """
    # convert strings to template
    if isinstance(template, Path):
        _template = env.get_template(str(template))
    else:
        _template = env.from_string(template)

    value = _template.render(**context)
    if isinstance(value, Undefined):
        value._fail_with_undefined_error()
    return value


def write_template(env: NativeEnvironment, src: Path, dest: Path, context: Any):
    """Utility function for rendering and writing a template file.

    Args:
        env: The Jinja2 environment to use for rendering
        src: The template file path
        dest: The path to write the rendered template to
        context: The context variables to use for rendering
    """
    template_rendered = render_template(env, src, context)
    with open(dest, "w") as f:
        # mappings and lists are output as yaml files
        if isinstance(template_rendered, Mapping) or (
            # need to exclude str types since they are also sequences
            not isinstance(template_rendered, Text)
            and isinstance(template_rendered, Sequence)
        ):
            yaml = YAML(typ="safe")
            yaml.dump(template_rendered, f)
        else:
            f.write(str(template_rendered))


class BaseObject(BaseModel):
    """Base model for template configuration models"""

    name: str = Field(
        ..., description="A descriptive name for the file template directive"
    )

    extra: Dict[str, Any] = Field(
        {},
        description="Dict that can be used to bind additional context info to a template object",
    )

    def dict(self, **kwargs):
        # set by alias to true by default
        # to ensure that template object fields are always serialized based
        # on their alias names
        kwargs.setdefault("by_alias", True)
        return super().dict(**kwargs)


class BaseFileObject(BaseObject):
    """Base model for file/directory type template objects"""

    src: str = Field(
        ...,
        description="The template source path (relative to the containing directory)",
    )

    dest: str = Field(
        ...,
        description="The templates destination path (relative to the containing directories destination path)",
    )

    delete: bool = Field(
        True,
        description="If the template object should be deleted after instantiating the TSM",
    )


class File(BaseFileObject):
    """File template model for configuring TIM template files"""

    type_: Literal["file"] = Field("file", alias="type")


class Directory(BaseFileObject):
    """Directory template model for configuring TIM template directories"""

    type_: Literal["dir"] = Field("dir", alias="type")

    copy_: List[str] = Field(
        [],
        description="List of file globs (relative to the dir) to copy as is",
        alias="copy",
    )

    contents: List[Union[File, "Directory"]] = Field(
        [], description="List of sub directories or files"
    )


Directory.update_forward_refs()


def get_yaml() -> YAML:
    """Utility function for creating a YAML parser and serializer.

    Returns:
        A ruamel.yaml.YAML object
    """
    yaml = YAML(typ="safe")
    for g in [File, Directory]:
        yaml.register_class(g)
    return yaml


def validate_object_list(object_list) -> List[Union[File, Directory]]:
    """Utility function for validating template object model lists.

    Args:
        object_list: List of unvalidated template object models.

    Returns:
        A validated list of template object models converted to the correct
        Python classes.
    """
    return parse_obj_as(
        Annotated[List[Union[File, Directory]], Field(discriminator="type")],
        object_list,
    )


def render_tim(
    env: NativeEnvironment,
    object_list: List[Union[File, Directory]],
    src_dir: Path,
    dest_dir: Path,
    global_context: Dict[str, Any],
    parent_context: Dict[str, Any] = {},
    delete_dirs: Optional[Deque[Path]] = None,
    delete_files: Optional[Deque[Path]] = None,
) -> Tuple[Deque[Path], Deque[Path]]:
    """Function for rendering a TIM using the context and template configuration.

    Args:
        env: The TIM Jinja2 environment.
        object_list: The list of template objects to render for the TIM.
        src_dir: The current source directory for template objects.
        dest_dir: The current destination directory for rendered templates.
        global_context: The global TIM context.
        parent_context: The TIM context specific to the parent template objects.
        delete_dirs: LiFo queue of directories to delete at the end of render process.
        delete_files: LiFo queue of files to delete at the end of render process.

    Raises:
        NotImplementedError: If the raw object_list contains an unknown template object type

    Returns:
        The final `delete_dirs` and `delete_files` queues as tuple `(delete_dirs, delete_files)`
    """

    if delete_dirs is None:
        delete_dirs = deque()
    if delete_files is None:
        delete_files = deque()

    for obj in object_list:
        src: Path = src_dir.joinpath(obj.src)
        dest: Path = dest_dir.joinpath(obj.dest)
        if isinstance(obj, Directory):
            # create the directory
            dest.mkdir(parents=True, exist_ok=True)

            # handle the copy configuration
            # i.e., resolve all globs and copy them to the destination
            for glb in obj.copy_:
                for copy_src in src.glob(glb):
                    copy_src_relative = copy_src.relative_to(src)
                    copy_dest = dest.joinpath(copy_src_relative)
                    # make sure the containing directory exists (might be needed if glob is for some sub dir)
                    copy_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(copy_src, copy_dest)

            # handle all sub template objects (dirs and files)
            new_parent_context = parent_context.copy()
            new_parent_context.update(obj.extra)
            if obj.delete and src not in delete_files:
                delete_dirs.append(src)
            render_tim(
                env,
                obj.contents,
                src,
                dest,
                global_context,
                new_parent_context,
                delete_dirs,
                delete_files,
            )

        elif isinstance(obj, File):
            context = {
                "context": global_context,
                "parent_context": parent_context,
                "local_context": obj.extra,
            }
            if obj.delete and src not in delete_files:
                delete_files.append(src)
            write_template(env, src, dest, context)
        else:
            raise NotImplementedError()

    return (delete_dirs, delete_files)
