import os
import logging

logging.getLogger().setLevel(logging.NOTSET)

class Logger(object):
    def __init__(self, **kwargs):
        name = kwargs.get("name", "Agently-Daily-News-Collector")
        log_level = kwargs.get("log_level", "ERROR")
        console_level = kwargs.get("console_level", "INFO")
        log_format = kwargs.get("format", "%(asctime)s\t[%(levelname)s]\t%(message)s")
        log_path = kwargs.get("path", "./logs/Agently_daily_news_collector.log")
        handlers = kwargs.get("handlers", [])
        self.logger = logging.getLogger(name)
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(getattr(logging, console_level))
        stream_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(stream_handler)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(file_handler)
        for handler in handlers:
            self.logger.addHandler(handler)

    def __transform(self, *args, **kwargs):
        message = ""
        for arg in args:
            message += f"{ arg }\t"
        message = message[:-1]
        kwargs_to_list = []
        kwargs_message = ""
        for key, value in kwargs.items():
            kwargs_to_list.append(f"{ key }: { str(value) }")
        kwargs_message += "\t".join(kwargs_to_list)
        if kwargs_message != "":
            message += f"\t{ kwargs_message }"
        return message

    def debug(self, *args, **kwargs):
        return self.logger.debug(self.__transform(*args, **kwargs))

    def info(self, *args, **kwargs):
        return self.logger.info(self.__transform(*args, **kwargs))

    def warning(self, *args, **kwargs):
        return self.logger.warning(self.__transform(*args, **kwargs))

    def error(self, *args, **kwargs):
        return self.logger.error(self.__transform(*args, **kwargs))

    def critical(self, *args, **kwargs):
        return self.logger.critical(self.__transform(*args, **kwargs))

logger = Logger()