import logging
import pathlib

import click

from . import log, malinka, misc

logger = logging.getLogger(__name__)


class ExitCode:
    GOODBYE_NOT_FOUND = 5
    GREETING_NOT_FOUND = 4
    MODEL_NOT_FOUND = 3
    SUCCESS = 0


@click.command()
@click.option(
    '-g', '--greeting',
    default='/usr/share/malinka/greeting.oga',
    help='Set path to the greeting song', type=str
)
@click.option(
    '-b', '--goodbye',
    default='/usr/share/malinka/greeting.oga',
    help='Set path to the greeting song', type=str
)
@click.option(
    '-l', '--log-file', default='/var/log/malinka.log',
    help='Set path to the log file', type=str
)
@click.option(
    '-p', '--pid-dir', default='/var/run/',
    help='Set path to the pid files', type=str
)
@click.option(
    '-m', '--model', default='/usr/share/malinka/model/',
    help='Set path to the language model', type=str
)
@click.option('--stop', is_flag=True, help='Stop malinka')
def main(goodbye: str, greeting: str, log_file: str, pid_dir: str, model: str, stop: bool) -> int:
    logfile = pathlib.Path(log_file).absolute()
    log.setup_logging(logfile)

    pid_dir = pathlib.Path(pid_dir).absolute()
    if (pid_dir / malinka.MALINKA_CONTROLLER_PIDFILE).exists():
        misc.kill_by_pid_file(pid_dir / malinka.MALINKA_CONTROLLER_PIDFILE)

    if not stop:
        model = pathlib.Path(model).absolute()
        if not model.exists():
            logger.error('No model found')
            return ExitCode.MODEL_NOT_FOUND

        goodbye = pathlib.Path(goodbye).absolute()
        if not goodbye.exists():
            logger.error('No goodbye found')
            return ExitCode.GOODBYE_NOT_FOUND

        greeting = pathlib.Path(greeting).absolute()
        if not greeting.exists():
            logger.error('No greeting found')
            return ExitCode.GREETING_NOT_FOUND

        malinka.MalinkaActivator.subprocess(
            goodbye=goodbye,
            greeting=greeting,
            pid_dir=pid_dir,
            logfile=logfile,
            model=model
        )
    return ExitCode.SUCCESS
