"""
This module contains all the core generator plugins shipped with the generator tool.
"""


from random import Random

from faker import Faker
from numpy.random import Generator as NumpyRandomGenerator
from numpy.random import default_rng as numpy_default_rng

from .plugin import Generator
from .random import SeedStore


class RandomGenerator(Generator):
    """Generator exposing the python random library

    See https://docs.python.org/3/library/random.html

    Examples:
        ```yaml
        foo: bar
        time: "{{ random.randint(0, 11) }}:{{ random.randint(0, 59) }}"
        ```
    """

    @property
    def name(self) -> str:
        """The generator name"""
        return "random"

    def create(self, seed_store: SeedStore) -> Random:
        """Creates a Random object and initialized with the next seed from the seed store.

        Args:
            seed_store: The seed store to use for getting the seed

        Returns:
            Python Random object
        """
        return Random(seed_store.next())


class FakerGenerator(Generator):
    """Generator exposing a faker object

    The created faker object is configured to support all
    available locales, but will default to en_UK, en_US (in order).
    A locale can be specified through the array access.

    Examples:
        ```yaml
            user:
                name: "{{ faker["jp_JP"].name() }}"
                title: "{{ faker.suffix() }}"
                address: "{{ faker["de_AT"].address() }}"
        ```

    See https://faker.readthedocs.io/en/master/providers.html
    """

    @property
    def name(self) -> str:
        """The generators name"""
        return "faker"

    def create(self, seed_store: SeedStore) -> Faker:
        """Creates a faker object initialized with a seed from the given seed store.

        Args:
            seed_store: The seed store to use

        Returns:
            Faker object with all locales available
        """
        locales = ["en_UK", "en_US"]
        faker = Faker(locale=locales)
        Faker.seed(seed_store.next())
        return faker


class NumpyGenerator(Generator):
    """Generator exposing the numpy libraries random API

    See https://numpy.org/doc/stable/reference/random/generator.html

    Examples:
        ```yaml
            {% set company_names = ["ACME", "XYZ Ltd.", "Umbrella CORP.", "Mom and Pop", "Contoso", "Oceanic Airlines"] %}
            companies:
            {% for company in numpy.choices(company_names, size=3) %}
                - name: {{ company }}
                  address: {{ faker.address() }}
            {% endfor %}
        ```
    """

    @property
    def name(self) -> str:
        """The name of the generator"""
        return "numpy"

    def create(self, seed_store: SeedStore) -> NumpyRandomGenerator:
        """Creates a numpy RandomGenerator object initialized with a seed from the given seed store.

        Args:
            seed_store: The seed store to use

        Returns:
            numpy RandomGenerator object
        """
        return numpy_default_rng(seed=abs(seed_store.next()))
