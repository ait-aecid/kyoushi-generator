from random import Random

from faker import Faker
from faker.config import AVAILABLE_LOCALES
from numpy.random import Generator as NumpyRandomGenerator
from numpy.random import default_rng as numpy_default_rng

from .plugin import Generator
from .random import SeedStore


class RandomGenerator(Generator):
    @property
    def name(self) -> str:
        return "random"

    def create(self, seed_store: SeedStore) -> Random:
        return Random(seed_store.next())


class FakerGenerator(Generator):
    @property
    def name(self) -> str:
        return "faker"

    def create(self, seed_store: SeedStore) -> Faker:
        locales = ["en_UK", "en_US", "de_DE", "de_AT"]
        locales.extend(AVAILABLE_LOCALES)
        # removing fr_QC since its deprecated in favor of fr_CA
        locales.remove("fr_QC")
        faker = Faker(locale=locales)
        Faker.seed(seed_store.next())
        return faker


class NumpyGenerator(Generator):
    @property
    def name(self) -> str:
        return "numpy"

    def create(self, seed_store: SeedStore) -> NumpyRandomGenerator:
        return numpy_default_rng(seed=abs(seed_store.next()))
