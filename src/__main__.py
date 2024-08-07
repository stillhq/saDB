#!/usr/bin/env python3
import os
import shutil
from typing import List
from urllib.parse import urljoin
import unittest

import click

import sadb.database as database
import sadb.source.manager as source_man
import sadb.yaml_parse as yaml_parse
import sadb.configuration as cfg
import sadb.utilities as util
import sadb.tests as tests

CONFIG = cfg.SadbConfig()

# Commandline Interface
@click.group()  # click group to allow subcommands
def cli():
    pass


@click.command()
def check_sources():
    """Tests to make sure all sources are correctly configured."""
    source_yaml = util.download_yaml(
        urljoin(CONFIG.repo_url, "sourceconf.yaml"), verbose=CONFIG.verbose
    )
    correct, error = source_man.check_sources(source_yaml)
    if not correct:
        print("Source check failed. Please run 'sadb update_source' with root to fix sources.")
        raise error
    print("All sources are correctly configured.")
    exit(0)


@click.command()
def update_source():
    """Downloads source data and generates source files."""
    # Check root
    if os.geteuid() != 0:
        print("This command must be run as root.")
        exit(1)

    if CONFIG.verbose:
        print("Downloading source data (1/2):")
    source_yaml = util.download_yaml(urljoin(CONFIG.repo_url, "sourceconf.yaml"), verbose=CONFIG.verbose)
    if CONFIG.verbose:
        print("\nGenerating sources (2/2)")
    source_man.generate_sources(source_yaml)
    exit(0)


@click.command()
def update_db(start_step: int = 0):
    """Updates the database with the latest yaml data."""
    if CONFIG.verbose:
        print(f"\nDownloading yaml database ({start_step + 1}/{start_step + 2}):")
    db_yaml = util.download_yaml(urljoin(CONFIG.repo_url, "repo.yaml"), verbose=CONFIG.verbose)
    # Add apps to database
    if CONFIG.verbose:
        print(f"\n(Re)generating database ({start_step + 2}/{start_step + 2})")
    with database.WritableDB(CONFIG) as db:
        db.clear_db()
        db.add_apps(yaml_parse.get_apps_from_yaml(db_yaml))


@click.command()
def update():
    """Runs both update_source and update_db. (Requires root)"""
    if os.geteuid() != 0:
        print("This command must be run as root.")
        exit(1)
    update_source()
    update_db(start_step=2)
    update_installed()


@click.command()
def get_db_location():
    """Outputs the location of the database."""
    print(CONFIG.db_location)


@click.command()
def update_installed():
    """Updates the installed apps database."""
    with database.WritableDB(CONFIG) as db:
        db.clear_installed_apps()
        for source in source_man.sources.values():
            source.add_installed_to_db(db)


@click.command(hidden=True)
def run_tests():
    """Runs the tests for the program."""
    unittest.main(module=tests, exit=False, argv=['ignore first arg'], verbosity=2)
    shutil.rmtree("sources", ignore_errors=True)
    shutil.rmtree("test", ignore_errors=True)


cli.add_command(check_sources)
cli.add_command(update_source)
cli.add_command(update_db)
cli.add_command(update)
cli.add_command(update_installed)
cli.add_command(get_db_location)
cli.add_command(run_tests)


if __name__ == "__main__":
    CONFIG.verbose = True
    cli()