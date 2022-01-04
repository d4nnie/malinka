import json
import logging
import pathlib
import queue
from typing import Callable, Dict

import sounddevice
import vosk

DEFAULT_AUDIO_BLOCK_SIZE = 8000  # bytes

# The most optimal channels count for 
# recognition on Asus Zenbook 13 internal micro

DEFAULT_CHANNELS_COUNT = 1

logger = logging.getLogger(__name__)


class Recognizer:
    def __init__(self, model: pathlib.Path, commands: Dict[str, Callable]) -> None:
        self._commands = commands
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

    def _process_speech(self, speech) -> None:
        commands = self._commands.keys()
        try:
            command = next(command for command in commands if command in speech)
        except StopIteration:
            return
        else:
            logger.info('Executing command "{}"...'.format(command))
            self._commands[command](speech)

    def _run_recognition_loop(self) -> None:
        recognizer = vosk.KaldiRecognizer(vosk.Model(self._modelpath), self._samplerate)
        while True:
            speech = self._recognize_sample(self._queue.get(), recognizer)
            if speech is not None:
                logger.debug('Recognized speech: {}'.format(speech))
                self._process_speech(speech)

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
