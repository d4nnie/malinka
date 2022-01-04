import abc
import json
import logging
import pathlib
import queue
import subprocess
import time
from typing import Any, Dict, Union

import sounddevice
import vosk

from . import log, misc

DEFAULT_AUDIO_BLOCK_SIZE = 8000  # bytes

# The most optimal channels count for 
# recognition on Asus Zenbook 13 internal micro

DEFAULT_CHANNELS_COUNT = 1

MALINKA_CONTROLLER_PIDFILE = 'malinka-controller.pid'
MALINKA_LISTENING_TIME = 8  # s

logger = logging.getLogger(__name__)


class SpeechProcessor(abc.ABC):
    @abc.abstractmethod
    def process(self, speech: str) -> None:
        """Processes received and recognized speech."""


class MalinkaActivator:
    class _SpeechProcessor(SpeechProcessor):
        def __init__(
            self, greeting: Union[str, pathlib.Path],
            goodbye: Union[str, pathlib.Path], name: str
        ) -> None:
            self._greeting = greeting
            self._goodbye = goodbye
            self._name = name

        def process(self, speech: str) -> None:
            if self._name in speech:
                MalinkaActivator._activate(self._greeting, self._goodbye)

    @staticmethod
    def _activate(greeting, goodbye, _=None):
        logger.info('Switching to active mode...')
        misc.play_sound(greeting)
        time.sleep(MALINKA_LISTENING_TIME)

        logger.info('Switching to suspended mode...')
        misc.play_sound(goodbye)

    @staticmethod
    def launch(**kwargs: Dict[str, Any]) -> None:
        log.setup_logging(kwargs['logfile'])
        recognizer_instance = Recognizer(kwargs['model'], MalinkaActivator._SpeechProcessor(
            name='малинка', goodbye=kwargs['goodbye'], greeting=kwargs['greeting']
        ))
        recognizer_instance.start_recognition()

    @staticmethod
    def subprocess(**kwargs: Dict[str, Any]) -> None:
        pid = subprocess.Popen(
            [
                '/usr/bin/env', 'python3', '-c',
                'from malinka import malinka\n'
                'malinka.MalinkaActivator.launch(\n'
                f'''    greeting="{kwargs['greeting']}",\n'''
                f'''    goodbye="{kwargs['goodbye']}",\n'''
                f'''    logfile="{kwargs['logfile']}",\n'''
                f'''    model="{kwargs['model']}"\n'''
                ')'
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).pid
        logger.info(f'Started malinka activator, pid: {pid}')
        misc.save_pid_to_file(kwargs['pid_dir'] / MALINKA_CONTROLLER_PIDFILE, pid)


class Recognizer:
    def __init__(self, model: pathlib.Path, processor: SpeechProcessor) -> None:
        self._processor = processor
        self._queue = queue.Queue()

        device_info = sounddevice.query_devices(None, 'input')
        self._samplerate = int(device_info['default_samplerate'])
        self._modelpath = str(model)

    def _on_audio_block_received(self, *args):
        data, status = args[0], args[3]
        if status:
            logger.warning('Failed to receive audio block, status: {}'.format(status))
        self._queue.put(bytes(data))

    def _recognize_sample(self, data, recognizer):
        if recognizer.AcceptWaveform(data):
            return json.loads(recognizer.Result())['text'].lower() or None

    def _run_recognition_loop(self):
        recognizer = vosk.KaldiRecognizer(vosk.Model(self._modelpath), self._samplerate)
        while True:
            speech = self._recognize_sample(self._queue.get(), recognizer)
            if speech is not None:
                logger.debug('Recognized speech: {}'.format(speech))
                self._processor.process(speech)

    def start_recognition(self) -> None:
        with sounddevice.RawInputStream(
            samplerate=self._samplerate,
            blocksize=DEFAULT_AUDIO_BLOCK_SIZE,
            device=None,
            channels=DEFAULT_CHANNELS_COUNT,
            dtype='int16',
            callback=self._on_audio_block_received
        ):
            logger.info('Starting recognition...')
            self._run_recognition_loop()
