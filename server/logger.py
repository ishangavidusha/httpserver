import time

class Logger:
    """
    A class that provides logging functionality with different log levels.

    Attributes:
        LEVELS (dict): A dictionary mapping log levels to their corresponding integer values.
        level (int): The current log level.

    Methods:
        __init__(self, level="INFO"): Initializes a Logger object with the specified log level.
        log(self, level, message): Logs a message with the specified log level.
        debug(self, message): Logs a debug message.
        info(self, message): Logs an info message.
        warning(self, message): Logs a warning message.
        error(self, message): Logs an error message.
        critical(self, message): Logs a critical message.
    """
    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}

    def __init__(self, level="INFO"):
        self.level = self.LEVELS[level]

    def log(self, level, message):
        if self.LEVELS[level] >= self.level:
            timestamp = time.localtime()
            print(
                f"{timestamp[0]}-{timestamp[1]:02d}-{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d} [{level}] {message}"
            )

    def debug(self, message):
        """
        Logs a debug message.

        Parameters:
        - message (str): The message to be logged.

        Returns:
        - None
        """
        self.log("DEBUG", message)

    def info(self, message):
        """
        Logs an informational message.

        Parameters:
            message (str): The message to be logged.

        Returns:
            None
        """
        self.log("INFO", message)

    def warning(self, message):
        """
        Logs a warning message.

        Parameters:
        - message (str): The warning message to be logged.
        """
        self.log("WARNING", message)

    def error(self, message):
        """
        Logs an error message.

        Parameters:
            message (str): The error message to be logged.
        """
        self.log("ERROR", message)

    def critical(self, message):
        """
        Log a critical message.

        Parameters:
        - message (str): The message to be logged.

        Returns:
        - None
        """
        self.log("CRITICAL", message)