"""
The random module contains utility classes and functions that might be useful
for general purpose randomization.
"""

import sys

from random import Random


class SeedStore:
    """Utility class for generating PRNG seeds based on a single root seed.

    A SeedStore object can also be used like an iterator to generate multiple seeds.

    Examples:
        ```python
        store = SeedStore(1337)
        first = next(store)
        print(f"First seed {first}")
        for i,s in enumerate(store, 0):
            if i >= 10:
                break
            print(s)
        ```
    """

    mother_seed: int

    def __init__(self, mother_seed: int):
        """
        Args:
            mother_seed: The root seed from which all other seeds are generated from
        """
        self.mother_seed = mother_seed
        self._random = Random(mother_seed)

    def __iter__(self):
        return self

    def __next__(self) -> int:
        return self._random.randint(sys.maxsize * -1, sys.maxsize)

    def next(self) -> int:
        """Creates the next PRNG seed from the store

        Returns:
            A random int seed
        """
        return self.__next__()
