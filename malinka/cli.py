import json
import logging
import os
import pathlib
from typing import Union
import configparser

import click

from . import malinka, misc

MALINKA_CONFIG = '.malinkarc'
MALINKA_CONFIG_DIR = pathlib.Path(os.environ.get('MALINKA_CONFIG_DIR', '/etc/malinka/'))


def setup_logging(logfile: Union[str, pathlib.Path]) -> None:
    logging.basicConfig(
        filename=logfile,
        filemode='a',
        level=logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    )


def _read_config():
    config = configparser.ConfigParser()
    if (pathlib.Path(os.getcwd()) / MALINKA_CONFIG).exists():
        config.read(pathlib.Path(os.getcwd()) / MALINKA_CONFIG)
    elif (MALINKA_CONFIG_DIR / MALINKA_CONFIG).exists():
        config.read(MALINKA_CONFIG_DIR / MALINKA_CONFIG)
    else:
        raise RuntimeError('Failed to found malinka configuration file')
    return config


class ExitCode:
    FILE_NOT_FOUND = 3
    SUCCESS = 0


@click.command()
@click.option('--create-config', is_flag=True, help='Create template config with default values.')
@click.option('--stop', is_flag=True, help='Stop malinka voice assistant.')
def main(create_config: bool, stop: bool) -> int:
    if create_config:
        raise NotImplementedError()
    config = _read_config()

    setup_logging(pathlib.Path(config['logging']['Path']))
    if pathlib.Path(config['misc']['PIDDirectory']).exists():
        misc.kill_by_pid_file(
            pathlib.Path(config['misc']['PIDDirectory']) / malinka.MALINKA_CONTROLLER_PIDFILE
        )

    if not stop:
        if not pathlib.Path(config['malinka']['Model']).exists():
            return ExitCode.FILE_NOT_FOUND
        if not pathlib.Path(config['malinka']['Goodbye']).exists():
            return ExitCode.FILE_NOT_FOUND
        if not pathlib.Path(config['malinka']['Greeting']).exists():
            return ExitCode.FILE_NOT_FOUND

        malinka.MalinkaActivator.subprocess(
            name=config['malinka']['Name'],
            goodbye=pathlib.Path(config['malinka']['Goodbye']),
            greeting=pathlib.Path(config['malinka']['Greeting']),
            pid_dir=pathlib.Path(config['misc']['PIDDirectory']),
            logfile=pathlib.Path(config['logging']['Path']),
            model=pathlib.Path(config['malinka']['Model'])
        )
    return ExitCode.SUCCESS
