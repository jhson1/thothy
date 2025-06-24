import os
from typing import Any
import logging
from logging import Logger
import json


class PrintingLogger(Logger):
    def __init__(self, name="PrintingLogger"):
        super().__init__(name)

    def info(self, msg, *args, **kwargs):
        extra = kwargs.get('extra')
        logging.info(f"[PrintingLogger:msg] {msg}")
        if extra is not None:
            logging.info(
                f"[PrintingLogger:extra] {json.dumps(extra, indent=2)}")
        super().info(msg, *args, **kwargs)


class LoggingService:

    def __init__(self):
        self._logger = PrintingLogger()

        # TODO: Handle blocking functions in the future
        log_file_path = os.path.join(
            os.getenv("APP_DATA_DIRECTORY"), "logs", "api.log")
        print(f"Log file path: {log_file_path}")
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        self._logger.addHandler(logging.FileHandler(log_file_path))

    @property
    def logger(self) -> Logger:
        return self._logger

    def message(self, msg: Any):
        return {"msg": msg}
