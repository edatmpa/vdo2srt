"""
Entry point for `python -m src` and `python src/__main__.py`.
Delegates to cli.main().
"""

from src.cli import main

if __name__ == "__main__":
    main()
