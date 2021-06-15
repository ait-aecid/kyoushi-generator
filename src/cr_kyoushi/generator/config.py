import re

from typing import (
    List,
    Pattern,
)

from pydantic import (
    BaseModel,
    Field,
)


class PluginConfig(BaseModel):
    """Configuration options for the state machine factory plugin system."""

    include_names: List[Pattern] = Field(
        [re.compile(r".*")],
        description="A list of regular expressions used to define which plugins to include.",
    )
    exclude_names: List[Pattern] = Field(
        [],
        description="A list of regular expressions used to define \
        which plugins to explicitly exclude.",
    )
