import logging
import pathlib


def setup_logging(logfile: pathlib.Path) -> None:
    logging.basicConfig(
        filename=logfile,
        filemode='a',
        level=logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    )
