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
import platform
import sys
import sysconfig


class PKSystem:
    @staticmethod
    def get_platform():
        """Return a string with current platform (system and machine architecture).

        This attempts to improve upon `sysconfig.get_platform` by fixing some
        issues when running a Python interpreter with a different architecture than
        that of the system (e.g. 32bit on 64bit system, or a multiarch build),
        which should return the machine architecture of the currently running
        interpreter rather than that of the system (which didn't seem to work
        properly). The reported machine architectures follow platform-specific
        naming conventions (e.g. "x86_64" on Linux, but "x64" on Windows).

        Example output strings for common platforms:

            darwin_(ppc|ppc64|i368|x86_64|arm64)
            linux_(i686|x86_64|armv7l|aarch64)
            windows_(x86|x64|arm32|arm64)

        """

        system = platform.system().lower()
        machine = sysconfig.get_platform()
        machineArch = sysconfig.get_platform().split("-")[-1].lower()
        useableArch = machineArch
        is_64bit = sys.maxsize > 2**32

        if system == "darwin":  # get machine architecture of multiarch binaries
            if any([x in machineArch for x in ("fat", "intel", "universal")]):
                machineArch = platform.machine().lower()

        elif system == "linux":  # fix running 32bit interpreter on 64bit system
            if not is_64bit and machineArch == "x86_64":
                machineArch = "i686"
            elif not is_64bit and machineArch == "aarch64":
                machineArch = "armv7l"

        elif system == "windows":  # return more precise machine architecture names
            if machineArch == "amd64":
                machineArch = "x64"
            elif machineArch == "win32":
                if is_64bit:
                    machineArch = platform.machine().lower()
                else:
                    machineArch = "x86"

        # some more fixes based on examples in
        # https://en.wikipedia.org/wiki/Uname
        if not is_64bit and machineArch in ("x86_64", "amd64"):
            if any([x in system for x in ("cygwin", "mingw", "msys")]):
                machineArch = "i686"
            else:
                machineArch = "i386"
        inContainer = os.environ.get("PKSCREENER_DOCKER", "").lower() in (
            "yes",
            "y",
            "on",
            "true",
            "1",
        )
        sysVersion = f"{sys.version_info.major}.{sys.version_info.minor}.{
            sys.version_info.micro
        }"
        sysVersion = sysVersion if not inContainer else f"{sysVersion} (Docker)"
        useableArch = (
            "arm64"
            if any([x in machineArch for x in ("aarch64", "arm64", "arm")])
            else "x64"
        )
        return (
            f"Python {sysVersion}, {system}_{machineArch}: {machine}",
            machine,
            system,
            machineArch,
            useableArch,
        )
