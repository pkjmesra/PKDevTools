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
import subprocess


def downloadFolder(
    localPath: str = None,
    repoPath: str = None,
    branchName: str = None,
    folderName: str = None,
):
    if localPath is None or len(localPath.strip()) == 0:
        raise ValueError("localPath cannot be empty!")
    if repoPath is None or len(repoPath.strip()) == 0 or "/" not in repoPath:
        raise ValueError(
            "repoPath cannot be empty or invalid. You must provide repoPath in OWNER/REPO_Name or https://github.com/OWNER/REPO_Name or https://github.com/OWNER/REPO_Name.git format!"
        )
    if branchName is None or len(branchName.strip()) == 0:
        raise ValueError("branchName cannot be empty!")
    if folderName is None or len(folderName.strip()) == 0:
        raise ValueError("folderName cannot be empty!")
    rootFolderName = repoPath.split("/")[-1]
    if not repoPath.lower().endswith(".git"):
        repoPath = f"{repoPath}.git"
    if not repoPath.lower().startswith("https://github.com/"):
        repoPath = f"https://github.com/{repoPath}"

    destinationFolder = os.path.join(localPath, rootFolderName, folderName)

    os.makedirs(os.path.dirname(f"{localPath}{os.sep}"), exist_ok=True)
    command = f"cd {localPath} >/dev/null 2>&1 && git clone -n --depth=1 --branch {branchName} --filter=tree:0 {repoPath} >/dev/null 2>&1 && cd {rootFolderName} >/dev/null 2>&1 && git sparse-checkout set --no-cone {folderName} >/dev/null 2>&1 && git checkout >/dev/null 2>&1"
    os.system(command)
    command = f"cd {destinationFolder} >/dev/null 2>&1 && git status >/dev/null 2>&1 && git pull >/dev/null 2>&1"
    os.system(command)
    return destinationFolder


# from PKDevTools.classes import Archiver
# downloadFolder(Archiver.get_user_outputs_dir(),"pkjmesra/pkscreener","actions-data-download","actions-data-scan")
