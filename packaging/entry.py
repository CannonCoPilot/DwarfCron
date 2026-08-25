"""Entry point for the packaged chronicler binary."""
import multiprocessing
import sys

from chronicler.cli import cli

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(cli())
