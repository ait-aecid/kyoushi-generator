import shutil
import sys

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Sequence,
    Text,
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
):
    env = NativeEnvironment(
        loader=FileSystemLoader(template_dirs),
        undefined=StrictUndefined,
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
    )
    _add_env_options(env)
    return env


def create_context_environment(
    seed_store: SeedStore,
    generators: List[Generator] = [],
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./"),
):
    env = create_template_object_environment(template_dirs)
    for gen in generators:
        gen_instance = gen.create(seed_store)
        env.globals.update({gen.name: gen_instance})

    return env


def create_environment(
    config: JinjaConfig,
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./"),
    generators: List[Generator] = [],
):
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

    return env


def render_template(env: NativeEnvironment, template: Union[Text, Path], context: Any):
    print(f"Template {template}")
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
    name: str = Field(
        ..., description="A descriptive name for the file template directive"
    )

    extra: Dict[str, Any] = Field(
        {},
        description="Dict that can be used to bind additional context info to a template object",
    )


class BaseFileObject(BaseObject):
    src: str = Field(
        ...,
        description="The template source path (relative to the containing directory)",
    )

    dest: str = Field(
        ...,
        description="The templates destination path (relative to the containing directories destination path)",
    )


class File(BaseFileObject):
    type_: Literal["file"] = Field("file", alias="type")


class Directory(BaseFileObject):
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
    yaml = YAML(typ="safe")
    for g in [File, Directory]:
        yaml.register_class(g)
    return yaml


def validate_object_list(object_list) -> List[Union[File, Directory]]:
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
):
    for obj in object_list:
        src: Path = src_dir.joinpath(obj.src)
        dest: Path = dest_dir.joinpath(obj.dest)
        print("---")
        print(
            f"src: {src}, dest: {dest}, g: {global_context}, p: {parent_context}, obj: {obj}"
        )
        print("---")
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
            render_tim(env, obj.contents, src, dest, global_context, new_parent_context)

        elif isinstance(obj, File):
            context = {
                "context": global_context,
                "parent_context": parent_context,
                "local_context": obj.extra,
            }
            write_template(env, src, dest, context)
        else:
            raise NotImplementedError()
