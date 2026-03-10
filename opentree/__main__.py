"""
OpenTree entry point.

Allows running as: python -m opentree
"""

from opentree.app import OpenTreeApp


def main() -> None:
    """Run the OpenTree application."""
    app = OpenTreeApp()
    app.run()


if __name__ == "__main__":
    main()
