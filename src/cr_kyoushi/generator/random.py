import sys

from random import Random


class SeedStore:
    mother_seed: int

    def __init__(self, mother_seed: int):
        self.mother_seed = mother_seed
        self._random = Random(mother_seed)

    def __iter__(self):
        return self

    def __next__(self) -> int:
        return self._random.randint(sys.maxsize * -1, sys.maxsize)

    def next(self) -> int:
        return self.__next__()
