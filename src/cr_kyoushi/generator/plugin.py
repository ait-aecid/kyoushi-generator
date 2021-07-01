import sys

from typing import (
    Any,
    List,
    Optional,
    Type,
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
    def __init__(self):
        ...

    @property
    def name(self) -> str:
        ...

    def create(self, seed_store: SeedStore) -> Any:
        ...


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
            isinstance(ep.load()(), Generator)
        ):
            return class_

    return None


def get_generators(plugin_config: PluginConfig) -> List[Generator]:
    return [
        ep.load()()
        for ep in entry_points(group=GENERATOR_ENTRYPOINT)
        if _check_plugin_allowed(ep, plugin_config)
    ]
