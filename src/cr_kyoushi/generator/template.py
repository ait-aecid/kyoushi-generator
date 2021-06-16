from pathlib import Path
from typing import (
    Any,
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
from ruamel.yaml import YAML

from .config import JinjaConfig
from .plugin import Generator
from .random import SeedStore


def resolve_generators(data: Any, seed_store: SeedStore) -> Any:
    # handle sub dicts
    if isinstance(data, dict):
        data_rendered = {}
        for key, val in data.items():
            data_rendered[key] = resolve_generators(val, seed_store)
        return data_rendered

    # handle list elements
    if isinstance(data, list):
        return [resolve_generators(val, seed_store) for val in data]

    # resolve all actual generators
    if isinstance(data, Generator):
        data.setup(seed_store)
        return data.generate()

    # all other basic types are returned as is
    return data


def create_environment(
    config: JinjaConfig,
    template_dirs: Union[Text, Path, List[Union[Text, Path]]] = Path("./"),
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
    return env


def render_template(env: NativeEnvironment, template: Union[Text, Path], context: Any):
    # convert strings to template
    if isinstance(template, Path):
        _template = env.get_template(str(template))
    else:
        _template = env.from_string(template)

    value = _template.render(**context)

    if isinstance(value, Undefined):
        value._fail_with_undefined_error()
    return value


def write_template(
    yaml: YAML, env: NativeEnvironment, src: Path, dest: Path, context: Any
):
    template_rendered = render_template(env, src, context)
    with open(dest, "w") as f:
        # mappings and lists are output as yaml files
        if isinstance(template_rendered, Mapping) or (
            # need to exclude str types since they are also sequences
            not isinstance(template_rendered, Text)
            and isinstance(template_rendered, Sequence)
        ):
            yaml.dump(template_rendered, f)
        else:
            f.write(str(template_rendered))
