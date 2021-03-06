"""
This module contains the configuration model descriptions for the tool.
"""

import re

from typing import (
    Dict,
    List,
    Optional,
    Pattern,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
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


class MissingInput(BaseModel):
    """Canary class used to check if no input was passed.

    Objects of this class type are used as default values
    for the Input module. This makes it possible to check
    if an input value has been passed or not by using isinstance.
    We do this so we can also support passing in `None` values as
    input.
    """


class Input(BaseModel):
    """Model used for configuring CLI inputs.

    CLI inputs are configured as part ot the TIM
    configuration and must at least define a value
    model (i.e., Python type hint string for defining input type).
    Additionally it is also possible define a input value description
    and default value, as well make the input required.
    """

    model: str = Field(
        ..., description="The python type hint to use for loading this input"
    )
    required: bool = Field(False, description="If the input is required or not.")
    description: Optional[str] = Field(
        None, description="A textual description of the input variable"
    )
    value: Union[str, MissingInput] = Field(
        MissingInput(),
        description="The json encoded value assigned to the input",
        alias="default",
    )

    class Config:
        allow_population_by_field_name = True


class InputName(StrictStr):
    """Restricted string defining regex used to validate CLI input names."""

    regex = re.compile(r"^[\w\d-]*$")


InputVarsDict = Dict[InputName, str]
"""Type alias for dicts containing raw string encoded input variables"""
InputDict = Dict[InputName, Input]
"""Type alias for dicts containing parsed input variables"""


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
            inputs:
                employee_count:
                    model: int
                    required: true
                    description: Number of employees that should be simulated in the testbed.
                    prompt: Please enter the number of employees that should be created
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
    inputs: InputDict = Field(
        {},
        description="The TIMs input definitions used for receiving variables from the CLI",
    )
