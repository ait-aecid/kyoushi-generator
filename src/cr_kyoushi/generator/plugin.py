import sys

from typing import (
    Any,
    ClassVar,
    List,
    Optional,
    Type,
)

from pydantic import BaseModel
from ruamel.yaml import (
    YAML,
    Constructor,
    Node,
    Representer,
    ScalarNode,
)

from . import GENERATOR_ENTRYPOINT
from .config import PluginConfig
from .random import SeedStore


if sys.version_info >= (3, 8):
    from importlib.metadata import (
        EntryPoint,
        entry_points,
    )
    from typing import (
        Protocol,
        runtime_checkable,
    )
else:
    # need to use backport for python < 3.8
    from importlib_metadata import (
        EntryPoint,
        entry_points,
    )
    from typing_extensions import (
        Protocol,
        runtime_checkable,
    )


@runtime_checkable
class Generator(Protocol):
    @classmethod
    def to_yaml(cls, representer: Representer, node: "Generator"):
        ...

    @classmethod
    def from_yaml(cls, constructor: Constructor, node: Node) -> "Generator":
        ...

    def setup(self, seed_store: SeedStore):
        ...

    def generate(self) -> Any:
        ...


class GeneratorBase(BaseModel):
    yaml_tag: ClassVar[str]
    """The YAML tag name to use for this generator"""

    @classmethod
    def to_yaml(cls, representer: Representer, node: "GeneratorBase"):
        exclude = set()
        complex_values = []
        # handle all possible sub generators
        for k, v in dict(node).items():
            if isinstance(v, Generator):
                # add generators to exclude list so we don't serialize them twice
                exclude.add(k)
                # use the sub generators to_yaml to serialize it
                complex_values.append(
                    (representer.represent_str(k), v.to_yaml(representer, v))
                )

        # serialize all simple values
        map_node = representer.represent_mapping(
            cls.yaml_tag, node.dict(exclude=exclude)
        )
        # and combine with sub generators
        map_node.value = map_node.value + complex_values

        return map_node

    @classmethod
    def from_yaml(cls, constructor: Constructor, node: Node) -> "GeneratorBase":
        # scalar nodes are used for argumentless generators
        if isinstance(node, ScalarNode):
            return cls()
        # all other generators are passed their configuration parameters
        # through mapping keys
        return cls(**constructor.construct_mapping(node, deep=True))

    def setup(self, seed_store: SeedStore):
        raise NotImplementedError()

    def generate(self) -> Any:
        raise NotImplementedError()


def _check_plugin_allowed(
    ep: EntryPoint, plugin_config: PluginConfig
) -> Optional[Type[Generator]]:
    if (
        # entry point name must be in an include pattern
        any([pattern.match(ep.name) for pattern in plugin_config.include_names])
        # and not be excluded
        and not any([pattern.match(ep.name) for pattern in plugin_config.exclude_names])
    ):
        class_ = ep.load()
        if (
            # must implement the generator protcool
            issubclass(ep.load(), Generator)
            # must have a yaml tag
            and hasattr(class_, "yaml_tag")
        ):
            return class_

    return None


def get_generators(plugin_config: PluginConfig) -> List[Type[Generator]]:
    return [
        ep.load()
        for ep in entry_points(group=GENERATOR_ENTRYPOINT)
        if _check_plugin_allowed(ep, plugin_config)
    ]


def get_yaml(generators: List[Type[Generator]]) -> YAML:
    yaml = YAML(typ="safe")
    for g in generators:
        yaml.register_class(g)
    return yaml
