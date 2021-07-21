"""
This module contains the configuration model descriptions for the tool.
"""

import re

from typing import (
    List,
    Optional,
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


class JinjaConfig(BaseModel):
    """Configuration options for the jinja2 environment."""

    block_start: str = Field("\\{%", description="The block directives start string")
    block_end: str = Field("}", description="The block directives end string")

    variable_start: str = Field(
        "\\var{", description="The variable directives start string"
    )
    variable_end: str = Field("}", description="The variable directives end string")

    comment_start: str = Field(
        "\\{#", description="The comment directives start string"
    )
    comment_end: str = Field("}", description="The comment directives end string")

    line_statement: Optional[str] = Field(
        None, description="The string to indicate jinja2 line statements"
    )
    line_comment: Optional[str] = Field(
        None, description="The string to indicate jinja2 line comments"
    )


class Config(BaseModel):
    """Kyoushi Generator tool configuration model

    Examples:
        ```yaml
            seed: 1337
            plugin:
                include_names:
                    - .*
                exclude_names:
                    - evil\\..*
            jinja:
                block_start: '\\{%'
                block_end: '}'
                variable_start: '\\var{'
                variable_end: '}'
        ```
    """

    plugin: PluginConfig = Field(PluginConfig(), description="The plugin configuration")
    jinja: JinjaConfig = Field(
        JinjaConfig(), description="The jinja2 template engine configuration"
    )
    seed: Optional[int] = Field(
        None,
        description="A hard coded seed to use for instance creation with this model. Can be overwritten by CLI arguments.",
    )
