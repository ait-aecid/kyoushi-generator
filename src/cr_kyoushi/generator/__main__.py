"""
The main entrypoint for the package
"""

if __name__ == "__main__":
    import sys

    from .cli import cli

    cli(prog_name=f"{sys.executable} -m {__package__}")
