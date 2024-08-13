import logging


class LoggerConfigurator:
    def __init__(self, name, level=logging.DEBUG, log_file=None):
        self.name = name
        self.level = level
        self.log_file = log_file
        self.format = "%(asctime)s | %(name)s [%(levelname)s] %(message)s"

    def configure(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)

        # Create console handler and set level to debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)

        # Create and add custom formatter to the console handler
        formatter = logging.Formatter(self.format)
        console_handler.setFormatter(formatter)

        # Add the console handler to the logger
        logger.addHandler(console_handler)

        # If a log file is specified, add a file handler
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger
