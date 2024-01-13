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
# import argparse
import os
import platform

# argParser = argparse.ArgumentParser()
# required = False
# argParser.add_argument("-m", "--message", help="Commit message", required=required)
# argParser.add_argument(
#     "-b", "--branch", help="Origin branch name to push to", required=required
# )
# args = argParser.parse_known_args()
class Committer():
    def copySourceToDestination(srcPath="*.*",destPath=""):
        COPY_CMD = "cp"
        if "Windows" in platform.system():
            COPY_CMD = "copy"
        Committer.execOSCommand(f"{COPY_CMD} {srcPath} {destPath}")

    def commitTempOutcomes(addPath="*.*",commitMessage="[Temp-Commit]",branchName="gh-pages"):
        '''

        '''
        Committer.execOSCommand("git config user.name github-actions")
        Committer.execOSCommand("git config user.email github-actions@github.com")
        Committer.execOSCommand("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'")
        Committer.execOSCommand("git remote update")
        Committer.execOSCommand("git fetch")
        Committer.execOSCommand("git pull")
        Committer.execOSCommand(f"git add {addPath} --force")
        Committer.execOSCommand(f"git commit -m '{commitMessage}'")
        Committer.execOSCommand("git pull")
        Committer.execOSCommand(f"git push -v -u origin +{branchName}")

    def execOSCommand(command):
        try:
            os.system(command)
        except Exception:
            pass
