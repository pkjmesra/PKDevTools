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

import datetime

# import argparse
import os
import platform

import pytz

from PKDevTools.classes.log import default_logger


# argParser = argparse.ArgumentParser()
# required = False
# argParser.add_argument("-m", "--message", help="Commit message", required=required)
# argParser.add_argument(
#     "-b", "--branch", help="Origin branch name to push to", required=required
# )
# args = argParser.parse_known_args()
class Committer:
    def copySourceToDestination(srcPath="*.*", destPath=""):
        COPY_CMD = "cp"
        if "Windows" in platform.system():
            COPY_CMD = "copy"
        Committer.execOSCommand(f"{COPY_CMD} {srcPath} {destPath}")

    def commitTempOutcomes(
        addPath="*.*",
        commitMessage="[Temp-Commit]",
        branchName="gh-pages",
        showStatus=False,
    ):
        """ """
        cwd = os.getcwd()
        if not cwd.endswith(os.sep):
            cwd = f"{cwd}{os.sep}"
        addPath = addPath.replace(cwd, "")
        suffix = ">/dev/null 2>&1" if not showStatus else "--verbose"
        Committer.execOSCommand(
            "git config user.name github-actions >/dev/null 2>&1")
        Committer.execOSCommand(
            "git config user.email github-actions@github.com >/dev/null 2>&1"
        )
        Committer.execOSCommand(
            "git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' >/dev/null 2>&1"
        )
        # git remote update will update all of your branches set to track remote ones,
        # but not merge any changes in. If you've not checkedout all remote branches,
        # this might take a while to update all branches if one of the branches
        # is heavy on data.
        # Committer.execOSCommand("git remote update >/dev/null 2>&1")
        # git fetch will update only the branch you're on, but not merge any changes in.
        # Committer.execOSCommand("git fetch >/dev/null 2>&1")
        Committer.execOSCommand("git config pull.rebase false >/dev/null 2>&1")
        if showStatus:
            Committer.execOSCommand("git status")
        # git pull will update and merge any remote changes of the current branch you're on.
        # This would be the one you use to update a local branch.
        # Only pull from specific branch in remote origin
        Committer.execOSCommand(f"git pull origin +{branchName} {suffix}")
        # Committer.execOSCommand("git checkout --ours .")
        # Committer.execOSCommand("git reset --hard")
        Committer.execOSCommand(f"git add {addPath} --force")
        Committer.execOSCommand(f"git commit -m '{commitMessage}'")
        # Committer.execOSCommand(f"git pull origin +{branchName} {suffix}")
        Committer.execOSCommand(
    f"git push -v -u origin +{branchName} {suffix}")

    def execOSCommand(command: str):
        try:
            default_logger().debug(
                f"{datetime.datetime.now(pytz.timezone('Asia/Kolkata'))} : {command}"
            )
            command.replace(">/dev/null 2>&1", "")
            os.system(f"{command} >/dev/null 2>&1")
        except Exception as e:
            try:
                print(
                    f"{datetime.datetime.now(pytz.timezone('Asia/Kolkata'))} : {
                        command
                    }\nException:\n{e}"
                )
                # We probably got into a conflict
                os.system("git checkout --ours . >/dev/null 2>&1")
                os.system(f"{command} >/dev/null 2>&1")
            except Exception as ex:
                print(
                    f"{datetime.datetime.now(pytz.timezone('Asia/Kolkata'))} : {
                        command
                    }\nException:\n{e}"
                )
                pass
            pass
