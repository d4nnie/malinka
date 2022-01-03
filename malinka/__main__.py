import json
import logging
import pathlib
import queue
import subprocess
import sys
from typing import Any, ByteString, Callable, Dict, List, Optional

import click
import nltk
import sounddevice

import vosk

DEFAULT_AUDIO_BLOCK_SIZE = 8000  # bytes

MODEL_NOT_FOUND = 3
SUCCESS = 0

logger = logging.getLogger(__name__)


def _in_speech(command: str, speech: str) -> bool:
    words = speech.split()
    try:
        next(word for word in words if nltk.edit_distance(command, word) < 3)
    except StopIteration:
        return False
    else:
        return True


class Recognizer:
    def __init__(self, model: pathlib.Path, commands: Dict[str, Callable]) -> None:
        self._commands = commands
        self._queue = queue.Queue()

        device_info = sounddevice.query_devices(None, 'input')
        self._samplerate = int(device_info['default_samplerate'])
        self._modelpath = str(model)

    def _on_audio_block_completed(self, *args: List[Any]) -> None:
        if args[3]:  # status
            logger.warning(args[3])
        self._queue.put(bytes(args[0]))  # data

    def _recognize_sample(self, data: ByteString, recognizer: vosk.KaldiRecognizer) -> None:
        if recognizer.AcceptWaveform(data):
            return json.loads(recognizer.Result())['text'].lower() or None

    def _process_speech(self, speech: str) -> None:
        commands = self._commands.keys()
        try:
            command = next(command for command in commands if _in_speech(command, speech))
        except StopIteration:
            return
        else:
            logger.info('Executing command...')
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
            device=None, channels=1, dtype='int16', 
            callback=self._on_audio_block_completed
        ):
            logger.info('Starting recognition...')
            self._run_recognition_loop()


def start_malinka_listening(_: Optional[str] = None) -> None:
    subprocess.Popen(
        [
            'gst-launch-1.0', 'filesrc',
            'location=/usr/share/sounds/Yaru/stereo/complete.oga',
            '!', 'oggdemux', '!', 'vorbisdec', '!', 'audioconvert',
            '!', 'audioresample', '!', 'pulsesink'
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


@click.command()
@click.option(
    '-l', '--log-file', default='malinka.log',
    help='Set path to the log file', type=str
)
@click.option(
    '-m', '--model', default='/usr/local/share/malinka/model',
    help='Set path to the offline model', type=str
)
def main(log_file: str, model: str):
    logging.basicConfig(
        filename=log_file, filemode='a', level=logging.DEBUG,
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    )

    model = pathlib.Path(model).absolute()
    if not model.exists():
        logger.error('No model found')
        return MODEL_NOT_FOUND

    recognizer = Recognizer(model, {
        'малинка': start_malinka_listening
    })
    recognizer.start_recognition()
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main())
        