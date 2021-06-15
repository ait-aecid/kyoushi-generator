from typing import Any

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
        return data.generate(seed_store)

    # all other basic types are returned as is
    return data
