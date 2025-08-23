"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import os
import sys
import time

from PKDevTools.classes.Singleton import SingletonMixin, SingletonType


class OutputControls(SingletonMixin, metaclass=SingletonType):
    from typing_extensions import Literal

    def __init__(self, enableMultipleLineOutput=False, enableUserInput=False):
        super(OutputControls, self).__init__()
        self.enableMultipleLineOutput = enableMultipleLineOutput or (
            "PKDevTools_Default_Log_Level" in os.environ.keys()
        )
        self.enableUserInput = enableUserInput or (
            "PKDevTools_Default_Log_Level" in os.environ.keys()
        )
        self.lines = 0
        self.timeit = "timeit" in os.environ.keys()
        if self.timeit:
            self.start_time = time.time()

    def takeUserInput(
        self, inputString=None, enableUserInput=False, defaultInput=None
    ) -> None:
        if not enableUserInput and not self.enableUserInput:
            return False if defaultInput is None else defaultInput
        return input(inputString) or defaultInput

    def printOutput(
        self,
        *values: object,
        sep: str | None = " ",
        end: str | None = "\n",
        flush: Literal[False] | bool = False,
        enableMultipleLineOutput=False,
    ) -> None:
        # end = '\r' if (not enableMultipleLineOutput) else end
        # flush = True if (not enableMultipleLineOutput) else flush
        if self.timeit:
            print(f"@{str('{:.2f}'.format(time.time() - self.start_time))}s:")
        print(*values, sep=sep, end=end, flush=flush)
        enableMultipleLineOutput = (
            self.enableMultipleLineOutput
            or enableMultipleLineOutput
            or ("PKDevTools_Default_Log_Level" in os.environ.keys())
        )
        lines = len(str(*values).splitlines())
        self.lines += lines
        if enableMultipleLineOutput:
            return
        if not self.enableMultipleLineOutput and not enableMultipleLineOutput:
            for _ in range(lines):
                sys.stdout.write("\x1b[1A")  # cursor up one line
                sys.stdout.write("\x1b[2K")  # delete the last line
            self.lines -= 1

    def moveCursorToStartPosition(self):
        for _ in range(self.lines):
            self.moveCursorUpLines(1)
            self.lines -= 1

    def moveCursorUpLines(self, lines):
        try:
            for _ in range(lines):
                if sys.stdout is not None:
                    sys.stdout.write("\x1b[1A")  # cursor up one line
                    sys.stdout.write("\x1b[2K")  # delete the last line
        except Exception:
            pass
