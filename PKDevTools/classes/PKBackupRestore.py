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
import threading
import time
import zipfile

import git
import requests

from PKDevTools.classes import Archiver
from PKDevTools.classes.Committer import Committer
from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes.OutputControls import OutputControls

# Configurations
DATA_DIR = f"results{os.sep}Data"  # Directory where the SQLite file is stored
ZIP_FILE_NAME = "yfinance.cache.zip"
DB_FILE = os.path.join(
    Archiver.get_user_data_dir(), "yfinance.cache"
)  # SQLite database file
ZIP_FILE = os.path.join(
    Archiver.get_user_data_dir(), ZIP_FILE_NAME
)  # Zipped file location
REPO_PATH = os.getcwd()
REPO_URL = PKEnvironment().allSecrets.get(
    "REPO_URL", "https://github.com/pkjmesra/PKScreener.git"
)  # GitHub Repo URL
BRANCH = os.getenv("BRANCH", "main")  # Git branch (default: main)
GITHUB_TOKEN = PKEnvironment().allSecrets.get(
    "GITHUB_TOKEN", ""
)  # GitHub Personal Access Token
GITHUB_ZIP_URL = f"{
    REPO_URL.lower()
    .replace('.git', '')
    .replace('github.com', 'raw.githubusercontent.com')
}/refs/heads/{BRANCH}/{DATA_DIR}/{ZIP_FILE_NAME}"  # URL to fetch the zip file

# Thread Lock for thread-safe operations
pk_backup_restore_lock = threading.Lock()


def ensure_directory():
    """Ensure results/Data directory exists."""
    os.makedirs(Archiver.get_user_data_dir(), exist_ok=True)


def zip_sqlite_file():
    """Compress the SQLite database into a zip file."""
    try:
        ensure_directory()
        with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(
                DB_FILE, os.path.basename(DB_FILE)
            )  # Store file without full path
        # OutputControls().printOutput(f"✅ Zipped {DB_FILE} -> {ZIP_FILE}")
    except Exception as e:
        OutputControls().printOutput(
            f"❌ Error zipping DB Cache for {REPO_URL.split('/')[3]}: {e}"
        )


def commit_and_push():
    """Commit and push the zipped SQLite file to GitHub."""
    try:
        with pk_backup_restore_lock:  # Ensure thread safety
            repo = git.Repo(REPO_PATH)
            # Set authenticated remote URL
            origin = repo.remote(name="origin")
            origin.set_url(
                REPO_URL
            )  # .lower().replace("github.com",f"{GITHUB_TOKEN}@github.com")
            origin.pull()
            repo.git.reset(
                "--hard",
                "origin/main",
                # Reset local branch to match remote (force discards upstream
                # changes)
            )
            repo.git.add(ZIP_FILE, f="-f")  # Add your changes
            repo.index.commit("🔄 Force update SQLite database backup")
            try:
                # Force push, ignoring upstream changes
                origin.push(force=True)
            except BaseException:
                pass
            Committer.commitTempOutcomes(
                addPath=ZIP_FILE,
                commitMessage="🔄 Force update SQLite database backup",
                branchName=BRANCH,
                showStatus="PKDevTools_Default_Log_Level" in os.environ.keys(),
            )
        # OutputControls().printOutput(f"✅ DB Cache backed up to {REPO_URL.split('/')[3]}!")
    except Exception as e:
        OutputControls().printOutput(
            f"❌ Error in DB Backup to {REPO_URL.split('/')[3]}: {e}"
        )


def backup_to_github():
    """Background function to zip and push database."""
    # OutputControls().printOutput("⏳ Starting DB Cache backup ...")
    zip_sqlite_file()
    commit_and_push()
    # OutputControls().printOutput(f"✅ Backup to {REPO_URL.split('/')[3]} completed.")


def restore_from_github():
    """Background function to download and unzip database."""
    # OutputControls().printOutput("⏳ Starting restore ...")
    download_zip_from_github()
    unzip_file()
    # OutputControls().printOutput(f"✅ Restore DB Cache completed from {REPO_URL.split('/')[3]}.")


def start_backup():
    """Trigger backup as a background thread."""
    backup_thread = threading.Thread(target=backup_to_github, daemon=True)
    backup_thread.start()


def restore_backup():
    """Trigger backup as a background thread."""
    backup_thread = threading.Thread(target=restore_from_github, daemon=True)
    backup_thread.start()


def download_zip_from_github(retries=3, chunk_size=8192):
    """Download the zipped file from GitHub with improved reliability."""
    try:
        ensure_directory()
        # headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        for attempt in range(retries):
            response = requests.get(GITHUB_ZIP_URL, stream=True)
            if response.status_code == 200:
                total_bytes_written = 0
                content_length = int(
                    response.headers.get("Content-Length", 0)
                )  # Expected size
                with open(ZIP_FILE, "wb") as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # Ensure the chunk is not empty
                            file.write(chunk)
                            total_bytes_written += len(chunk)
                if total_bytes_written >= content_length:
                    # OutputControls().printOutput(f"✅ Downloaded {ZIP_FILE} ({total_bytes_written} bytes) from GitHub.")
                    return
                else:
                    OutputControls().printOutput(
                        f"⚠️ Incomplete DB Cache download: {total_bytes_written}/{content_length} bytes. Retrying..."
                    )
                    time.sleep(1)  # Small delay before retrying
            else:
                OutputControls().printOutput(
                    f"❌ Failed to download DB Cache: {response.status_code}, {
                        response.text
                    }"
                )
        OutputControls().printOutput(
    f"❌ Download failed after {retries} attempts.")
    except Exception as e:
        OutputControls().printOutput(f"❌ Error downloading DB Cache: {e}")


def unzip_file():
    """Extract the SQLite database file from the zip archive into results/Data/."""
    try:
        ensure_directory()
        with zipfile.ZipFile(ZIP_FILE, "r") as zipf:
            zipf.extractall(
                Archiver.get_user_data_dir()
            )  # Extract inside results/Data/
            # for file in zipf.namelist():
            #     zipf.extract(file, Archiver.get_user_data_dir())
        # OutputControls().printOutput(f"✅ Extracted {DB_FILE} from {ZIP_FILE}")
    except Exception as e:
        OutputControls().printOutput(
            f"❌ Error unzipping DB Cache from {REPO_URL.split('/')[3]}: {e}"
        )


# if __name__ == "__main__":
#     while True:
#         user_input = input("\nEnter 'backup' to start backup, 'restore' to restore DB, or 'exit' to quit: ").strip().lower()

#         if user_input == "backup":
#             start_backup()
# time.sleep(2)  # Let the thread start before returning to main loop

#         elif user_input == "restore":
#             restore_backup()
# time.sleep(2)  # Let the thread start before returning to main loop

#         elif user_input == "exit":
#             OutputControls().printOutput("👋 Exiting...")
#             break

#         else:
#             OutputControls().printOutput("⚠️ Invalid command. Try 'backup', 'restore', or 'exit'.")
