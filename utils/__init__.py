import io
import os
import sys

import contextlib
import functools
import threading

import matplotlib.pyplot as plt
import numpy as np

from config import OUTPUT_FILE_PATH


def img_show(img, filename: str):
    img = img / 2 + 0.5
    np_img = img.numpy()
    plt.imshow(np.transpose(np_img, (1, 2, 0)))
    plt.savefig(filename)


def file_output(data: str):
    open_method = 'a' if file_output.count else 'w'
    lines = data.splitlines()
    with open(OUTPUT_FILE_PATH, open_method) as output_file:
        for line in lines:
            output_file.write(f'{line}\n')
    file_output.count += len(lines)


file_output.count = 0


@contextlib.contextmanager
def kill_stderr():  # context manager
    devnull = open(os.devnull, mode='w')
    with contextlib.redirect_stderr(devnull):
        yield
    devnull.close()


def without_stderr(func):  # decorator
    """Decorator that makes function run without stderr output."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with kill_stderr():
            return func(*args, **kwargs)
    return wrapper


class StdoutCatcher(
    contextlib.ContextDecorator,
    contextlib.AbstractContextManager
):  # context manager: available as str with subclassing
    """
    Context manager that catches stdout in context, and can be converted to string

    example usage:

        As context manager: simply used as context manager
            >>> output = StdoutCatcher()
            >>> with output:
            ...     print("Sample outputs")
            ...
            >>> str(output)
            "Sample outputs\n"

        As direct decorator: make function return stdout output string, instead of printing it.
            >>> @StdoutCatcher
            ... def simple_function():
            ...     print("Sample outputs")
            ...     return "Truncated return value"
            ...
            >>> simple_function()
            "Sample outputs\n"

        As initialized decorator: make function continuously stack stdout output to object, instead of printing it.
            >>> output = StdoutCatcher()
            >>> @output
            ... def simple_function():
            ...     print("Sample outputs")
            ...     return "Return value"
            ...
            >>> simple_function()
            "Return value"
            >>> simple_function()
            "Return value"
            >>> str(output)
            "Sample outputs\nSample outputs\n"

    """

    __stream = "stdout"

    def __new__(cls, func=None):
        if func is not None:  # as direct decorator
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with cls() as obj:
                    func(*args, **kwargs)
                return str(obj)
            return wrapper  # return not new object but decorator
        self = object.__new__(cls)
        self.__lock = threading.RLock()
        self.__target = None
        self.__wrapper = io.StringIO()
        return self

    __new__.__text_signature__ = '($cls, func=None, /)'

    def __enter__(self):
        if self.__target is None:
            with self.__lock:
                if self.__target is None:
                    # Double-checked
                    self.__target = getattr(sys, self.__stream)
                    setattr(sys, self.__stream, self.__wrapper)
        return self

    open = __enter__

    def __exit__(self, exc_type=None, exc_inst=None, exc_tb=None):
        if self.__target is not None:
            with self.__lock:
                if self.__target is not None:
                    setattr(sys, self.__stream, self.__target)
                    self.__target = None
        return

    close = __exit__

    def __str__(self):
        return self.__wrapper.getvalue()

    getvalue = __str__

    def __repr__(self):
        value = self.__str__()
        if not value:
            return "<%s object at %s (empty)>" % (type(self).__name__, hex(id(self)))
        return value

    def __call__(self, func):
        wrapper = super().__call__(func)
        wrapper.__output__ = self.__wrapper
        return wrapper


catch_stdout = StdoutCatcher  # alias
