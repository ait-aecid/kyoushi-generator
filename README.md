# Cyber Range Kyoushi - Generator
[![Pipeline Info](https://git-service.ait.ac.at/sct-cyberrange/tools/kyoushi/generator/badges/master/pipeline.svg)](https://git-service.ait.ac.at/sct-cyberrange/tools/kyoushi/generator/-/pipelines/latest)
[![Coverage Report](https://git-service.ait.ac.at/sct-cyberrange/tools/kyoushi/generator/badges/master/coverage.svg?style=flat)](https://git-service.ait.ac.at/sct-cyberrange/tools/kyoushi/generator/)
[![Latest Offline Docs](https://img.shields.io/badge/latest-Offline%20Docs-ceb48a)](https://git-service.ait.ac.at/sct-cyberrange/tools/kyoushi/generator/-/jobs/artifacts/master/raw/offline-docs.tar.gz?job=pages)

The Cyber Range Kyoushi Generator package provides a CLI tool that can be used to create randomized *Template Specific Models* (TSM) from *Template Independent Models* (TIM). TIMs can loaded either from GIT repositories or from the local file system. An existing TIM can be created running the following command (passing the seed parameter ensures reproducibility):

```bash
cr-kyoushi-generator apply --seed 42 \
        https://github.com/ait-aecid/kyoushi-testbed-tim \
        ~/Projects/kyoushi-testbed-tsm
```

## Template Independent Model (TIM) Format

A TIM is defined by two things:

 - **Model Configuration:** used to define the randomizable context variables and template rendering process.
 - **Model Template Directories and Files:** Testbed configuration files using Jinja2 template logic based on the context variables defined in the TIM configuration.

### Model Configuration

By default the Cyber Range Kyoushi Generator will search for the model configuration files in the TIM repositories `model` directory, but it is possible to change the search location through the `--model, -m` parameter.

The `model` directory should contain the following three files:

  - `config.yml` (Optional): The CLI configuration file for configuring the Jinja environment for TIM templates and generator plugins.
  - `context.yml.j2`: Jinja2 templated TIM context configuration file. This file is used to define all static and randomizable TIM context variables. For this Jinja2 template syntax can be used to define complex TIM logic and random data generator plugins to define context variables.
  - `templates.yml.j2`: A Jinja2 templated configuration file for defining the list of TIM templates that should be rendered during the TSM conversion process. Within this is rendered based on the fully initialized TIM context as such it is possible to define template files based on randomized variables. For example creating a configuration file for each randomly generated user.

### Example
