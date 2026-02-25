"""CLI application."""

import asyncio
import json
import sys
from pathlib import Path

import click

from docagentline.cli.commands import submit, status, results, metrics as metrics_cmd
from docagentline.observability import setup_logging


@click.group()
def cli():
    """DocAgentLine CLI - Document extraction pipeline."""
    setup_logging()


cli.add_command(submit.submit)
cli.add_command(status.status)
cli.add_command(results.results)
cli.add_command(metrics_cmd.metrics)


if __name__ == "__main__":
    cli()
