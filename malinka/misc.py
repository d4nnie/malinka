import logging
import os
import pathlib
import signal
from typing import Union

import vlc

logger = logging.getLogger(__name__)


def save_pid_to_file(path: Union[str, pathlib.Path], pid: int) -> None:
    try:
        with open(path, 'w') as file:
            file.write(str(pid))
    except (PermissionError, FileNotFoundError):
        logger.warning(f'Failed to save pid into {path}')


def kill_by_pid_file(path: Union[str, pathlib.Path]) -> None:
    try:
        with open(path, 'r') as file:
            pid = int(file.read())
    except (PermissionError, FileNotFoundError):
        return

    logger.debug(f'Killing process with pid: {pid}')
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.remove(path)


def play_sound(path: Union[str, pathlib.Path]) -> None:
    vlc.MediaPlayer(f'file://{path}').play()
