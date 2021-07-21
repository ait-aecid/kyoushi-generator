Random data generators shipped with the Cyber Range Kyoushi Generator CLI.

## Random (`random`)

::: cr_kyoushi.generator.core:RandomGenerator
    inherited_members: yes
    selection:
        filters:
            - "!^_"  # exlude all members starting with _
            - "^__init__$"  # but always include __init__ modules and methods
            - "!^name$"
    rendering:
        show_root_toc_entry: no
        show_object_full_path: yes
        heading_level: 3

## Faker (`faker`)

::: cr_kyoushi.generator.core:FakerGenerator
    inherited_members: yes
    selection:
        filters:
            - "!^_"  # exlude all members starting with _
            - "^__init__$"  # but always include __init__ modules and methods
            - "!^name$"
    rendering:
        show_root_toc_entry: no
        show_object_full_path: yes
        heading_level: 3

## Numpy (`numpy`)

::: cr_kyoushi.generator.core:NumpyGenerator
    inherited_members: yes
    selection:
        filters:
            - "!^_"  # exlude all members starting with _
            - "^__init__$"  # but always include __init__ modules and methods
            - "!^name$"
    rendering:
        show_root_toc_entry: no
        show_object_full_path: yes
        heading_level: 3
