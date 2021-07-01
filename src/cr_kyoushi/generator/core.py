from random import Random

from .plugin import Generator


class RandomGenerator(Generator):
    @property
    def name(self) -> str:
        return "random"

    def create(self, seed_store) -> Random:
        return Random(seed_store.next())
