import functools
import logging
import pathlib
import sys

import click
import vlc

from .recognizer import Recognizer

logger = logging.getLogger(__name__)


def _play_greeting(path):
    vlc.MediaPlayer('file://{}'.format(path)).play()


def _start_malinka_listening(greeting_path, _=None):
    _play_greeting(greeting_path)


class ExitCode:
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
    '-l', '--log-file', default='/var/log/malinka.log',
    help='Set path to the log file', type=str
)
@click.option(
    '-m', '--model', default='/usr/share/malinka/model/',
    help='Set path to the language model', type=str
)
def main(greeting: str, log_file: str, model: str) -> int:
    log_file = pathlib.Path(log_file).absolute()
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        level=logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    )

    model = pathlib.Path(model).absolute()
    if not model.exists():
        logger.error('No model found')
        return ExitCode.MODEL_NOT_FOUND

    greeting = pathlib.Path(greeting).absolute()
    if not greeting.exists():
        logger.error('No greeting found')
        return ExitCode.GREETING_NOT_FOUND

    recognizer = Recognizer(model, {
        'малинка': functools.partial(_start_malinka_listening, greeting)
    })
    recognizer.start_recognition()
    return ExitCode.SUCCESS


if __name__ == '__main__':
    sys.exit(main())
        