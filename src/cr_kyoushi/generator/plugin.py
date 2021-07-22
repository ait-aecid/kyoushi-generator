"""
The plugin module contains the interface definitions and utility functions used
to load generator plugins used in the TIM context templating configuration.
"""

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
    """Interface definition of generator plugin.

    Generator plugins can be added through the entry points system.
    A generator must have a name and a create method accepting a seed store.
    The create method must create some sort of random data generator object initialized
    with a seed/s from the given seed store.
    This object will then be available in TIM context templates Jinja2 logic.
    """

    def __init__(self):
        """Generators must have an init method requirering no arguments."""
        ...

    @property
    def name(self) -> str:
        """The name under which the random data generator object will be accessible."""
        ...

    def create(self, seed_store: SeedStore) -> Any:
        """The main function used to create random data generator objects.

        Args:
            seed_store: The seed store to be used for random seed generation.

        Returns:
            A random data generator object or function.
        """
        ...


def _check_plugin_allowed(
    ep: EntryPoint, plugin_config: PluginConfig
) -> Optional[Type[Generator]]:
    """Utility function used to check if the given entry point will be loaded.

    Args:
        ep: The entry point plugin
        plugin_config: The plugin configuration

    Returns:
        The loaded entry point or `None` if the configration policy disallows loading it.
    """
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
    """Utility function for getting a list of all available generator plugins.

    Args:
        plugin_config: The plugin configuration policy

    Returns:
        List of the loaded generator plugins.
    """
    return [
        ep.load()()
        for ep in entry_points(group=GENERATOR_ENTRYPOINT)
        if _check_plugin_allowed(ep, plugin_config)
    ]
