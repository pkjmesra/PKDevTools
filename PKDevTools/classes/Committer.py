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

import os
import time
import platform
import base64
import requests
import tempfile
import pytz
import tempfile
import subprocess
import shutil
import json
from pathlib import Path
from github import Github, InputGitTreeElement, GithubException

from PKDevTools.classes.log import default_logger

class Committer:
    def copySourceToDestination(srcPath="*.*", destPath="", showStatus=False):
        COPY_CMD = "cp"
        if "Windows" in platform.system():
            COPY_CMD = "copy"
        result = Committer.execOSCommand(f"{COPY_CMD} {srcPath} {destPath}", showStatus=showStatus)
        return result

    def commitTempOutcomes(
        addPath="*.*",
        commitMessage="[Temp-Commit]",
        branchName="gh-pages",
        showStatus=False,
        timeout = 300
    ):
        """ """
        cwd = os.getcwd()
        if not cwd.endswith(os.sep):
            cwd = f"{cwd}{os.sep}"
        addPath = addPath.replace(cwd, "")
        
        # Just execute commands - execOSCommand will handle verbose output capture
        Committer.execOSCommand("git config user.name github-actions", showStatus=showStatus, timeout=timeout)
        Committer.execOSCommand("git config user.email github-actions@github.com", showStatus=showStatus, timeout=timeout)
        Committer.execOSCommand("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'", showStatus=showStatus, timeout=timeout)
        # git remote update will update all of your branches set to track remote ones,
        # but not merge any changes in. If you've not checkedout all remote branches,
        # this might take a while to update all branches if one of the branches
        # is heavy on data.
        # Committer.execOSCommand("git remote update >/dev/null 2>&1")
        # git fetch will update only the branch you're on, but not merge any changes in.
        # Committer.execOSCommand("git fetch >/dev/null 2>&1")
        Committer.execOSCommand("git config pull.rebase false", showStatus=showStatus, timeout=timeout)
        
        if showStatus:
            Committer.execOSCommand("git status", showStatus=showStatus, timeout=timeout)
        # git pull will update and merge any remote changes of the current branch you're on.
        # This would be the one you use to update a local branch.
        # Only pull from specific branch in remote origin
        Committer.execOSCommand(f"git pull origin +{branchName}", showStatus=showStatus, timeout=timeout)
        Committer.execOSCommand(f"git add {addPath} --force", showStatus=showStatus, timeout=timeout)
        Committer.execOSCommand(f"git commit -m '{commitMessage}'", showStatus=showStatus, timeout=timeout)
        Committer.execOSCommand(f"git push -u origin +{branchName}", showStatus=showStatus, timeout=timeout)

    def execOSCommand(command: str, showStatus=False, timeout=300):
        """
        Universal command execution that works with any command
        """
        try:
            timestamp = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
            default_logger().info(f"{timestamp} : Executing: {command}")
            
            clean_command = command.strip()
            
            if showStatus:
                try:
                    # Always capture output for any command when showStatus=True
                    process = subprocess.Popen(
                        clean_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    stdout, stderr = process.communicate(timeout=timeout)
                    return_code = process.returncode
                    
                    # Log everything
                    log_message = f"Command executed: {clean_command}\n"
                    log_message += f"Exit code: {return_code}\n"
                    
                    if stdout:
                        log_message += f"Output:\n{stdout}\n"
                    if stderr:
                        log_message += f"Errors:\n{stderr}\n"
                    
                    default_logger().info(log_message)
                    
                    return {
                        'command': clean_command,
                        'return_code': return_code,
                        'stdout': stdout,
                        'stderr': stderr,
                        'success': return_code == 0
                    }
                    
                except subprocess.TimeoutExpired:
                    error_msg = f"Command timed out: {clean_command}"
                    default_logger().error(error_msg)
                    return {
                        'command': clean_command,
                        'return_code': -1,
                        'stdout': '',
                        'stderr': error_msg,
                        'success': False
                    }
                    
            else:
                # Silent execution
                return_code = os.system(f"{clean_command} >/dev/null 2>&1")
                return None
                
        except Exception as e:
            error_msg = f"Unexpected error for {clean_command}: {e}"
            default_logger().error(error_msg)
            return None

class GitHubCrossRepoCommitter:
    def __init__(self, github_token, org_name):
        """
        Initialize with GitHub token and organization name.
        
        Args:
            github_token (str): GitHub Personal Access Token with repo scope
            org_name (str): Organization or owner name
        """
        self.github_token = github_token
        self.org_name = org_name
        self.g = Github(github_token)
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.base_url = "https://api.github.com"

    def commit_to_repo(self, source_repo, target_repo, target_branch, 
                      file_path, file_content, commit_message, 
                      file_mode="100644", file_type="blob"):
        """
        Commit a file to another repository and branch.
        
        Args:
            source_repo (str): Source repository name (for reference)
            target_repo (str): Target repository name
            target_branch (str): Target branch name
            file_path (str): Path to file in target repository
            file_content (str): Content of the file
            commit_message (str): Commit message
            file_mode (str): File mode (100644 for normal files, 100755 for executables)
            file_type (str): File type (usually "blob")
            
        Returns:
            dict: Commit information
        """
        try:
            # Get target repository
            target_repo_obj = self.g.get_repo(f"{self.org_name}/{target_repo}")
            
            # Get reference to the target branch
            ref = target_repo_obj.get_git_ref(f"heads/{target_branch}")
            
            # Get current commit
            commit = target_repo_obj.get_commit(ref.object.sha)
            
            # Create blob with new file content
            blob = target_repo_obj.create_git_blob(file_content, "utf-8")
            
            # Create tree element for the file
            tree_element = InputGitTreeElement(
                path=file_path,
                mode=file_mode,
                type=file_type,
                sha=blob.sha
            )
            
            # Create new tree
            tree = target_repo_obj.create_git_tree([tree_element], base_tree=commit.tree)
            
            # Create new commit
            new_commit = target_repo_obj.create_git_commit(
                commit_message,
                tree,
                [commit]
            )
            
            # Update branch reference
            ref.edit(new_commit.sha)
            
            return {
                "success": True,
                "commit_sha": new_commit.sha,
                "commit_url": new_commit.html_url,
                "message": f"Successfully committed to {target_repo}/{target_branch}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to commit to {target_repo}/{target_branch}"
            }

    def commit_multiple_files(self, target_repo, target_branch, files_data, commit_message):
        """
        Commit multiple files to another repository.
        
        Args:
            target_repo (str): Target repository name
            target_branch (str): Target branch name
            files_data (list): List of dicts with 'path', 'content', 'mode'
            commit_message (str): Commit message
            
        Returns:
            dict: Commit information
        """
        try:
            target_repo_obj = self.g.get_repo(f"{self.org_name}/{target_repo}")
            ref = target_repo_obj.get_git_ref(f"heads/{target_branch}")
            commit = target_repo_obj.get_commit(ref.object.sha)
            
            tree_elements = []
            for file_data in files_data:
                blob = target_repo_obj.create_git_blob(
                    file_data['content'], 
                    "utf-8"
                )
                tree_element = InputGitTreeElement(
                    path=file_data['path'],
                    mode=file_data.get('mode', '100644'),
                    type='blob',
                    sha=blob.sha
                )
                tree_elements.append(tree_element)
            
            tree = target_repo_obj.create_git_tree(tree_elements, base_tree=commit.tree)
            new_commit = target_repo_obj.create_git_commit(commit_message, tree, [commit])
            ref.edit(new_commit.sha)
            
            return {
                "success": True,
                "commit_sha": new_commit.sha,
                "commit_url": new_commit.html_url,
                "message": f"Successfully committed {len(files_data)} files to {target_repo}/{target_branch}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to commit to {target_repo}/{target_branch}"
            }

    def create_or_update_file(self, target_repo, target_branch, file_path, content, commit_message):
        """
        Simple method to create or update a file using REST API.
        """
        url = f"{self.base_url}/repos/{self.org_name}/{target_repo}/contents/{file_path}"
        
        # Check if file exists to get its SHA
        response = requests.get(url, headers=self.headers, 
                              params={"ref": target_branch})
        
        data = {
            "message": commit_message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": target_branch
        }
        
        if response.status_code == 200:
            # File exists, include SHA for update
            data["sha"] = response.json()["sha"]
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "commit": response.json()["commit"],
                "message": f"File {file_path} updated in {target_repo}"
            }
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }

    def clone_and_commit(self, source_repo, target_repo, target_branch, 
                        files_to_commit, commit_message):
        """
        Clone, modify, and commit files (more complex but flexible).
        """
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone target repository
                clone_url = f"https://{self.github_token}@github.com/{self.org_name}/{target_repo}.git"
                os.system(f"git clone {clone_url} {temp_dir}")
                
                # Checkout target branch
                os.chdir(temp_dir)
                os.system(f"git checkout {target_branch}")
                
                # Add/modify files
                for file_path, content in files_to_commit.items():
                    file_dir = os.path.dirname(file_path)
                    if file_dir:
                        os.makedirs(file_dir, exist_ok=True)
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
                
                # Commit and push
                os.system('git add .')
                os.system(f'git commit -m "{commit_message}"')
                os.system(f'git push origin {target_branch}')
                
                return {"success": True, "message": "Commit completed successfully"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# Enhanced with error handling and logging
class SafeGitHubCommitter(GitHubCrossRepoCommitter):
    """
    >>> # Usage
    >>> committer = SafeGitHubCommitter(token, org_name)
    >>> result = committer.safe_commit(
    >>> target_repo="target-repo",
    >>> target_branch="main",
    >>> file_path="important-file.txt",
    >>> content="Critical update",
    >>> commit_message="Important automated update"
    >>> )

    """
    def __init__(self, github_token, org_name):
        """
        Initialize with GitHub token and organization name.
        
        Args:
            github_token (str): GitHub Personal Access Token with repo scope
            org_name (str): Organization or owner name
        """
        self.github_token = github_token
        self.org_name = org_name
        self.g = Github(github_token)
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.base_url = "https://api.github.com"

    def commit_large_binary_file(self, target_repo, target_branch, local_file_path, 
                                remote_file_path, commit_message, max_retries=3):
        """
        Commit a large binary file (like pickle files) to a GitHub repository
        without cloning the target repo. Uses direct API calls with chunked uploads.
        
        Args:
            target_repo (str): Target repository name
            target_branch (str): Target branch name
            local_file_path (str): Path to local file
            remote_file_path (str): Path in remote repository
            commit_message (str): Commit message
            max_retries (int): Number of retry attempts
            
        Returns:
            dict: Result of the operation

        # Example:
        >>> #Initialize the committer
        >>> committer = SafeGitHubCommitter("your_github_token", "your_org_name")

        >>> # Commit a large pickle file
        >>> result = committer.commit_large_binary_file(
        >>>     target_repo="target-repo-name",
        >>>     target_branch="main",
        >>>     local_file_path="/path/to/your/large/file.pkl",
        >>>     remote_file_path="data/important_file.pkl",  # Path in the remote repo
        >>>     commit_message="Adding large pickle file with important data"
        >>> )

        >>> if result['success']:
        >>>     print(f"Success! Commit URL: {result.get('commit_url', 'N/A')}")
        >>> else:
        >>>     print(f"Failed: {result.get('error', 'Unknown error')}")
        """
        for attempt in range(max_retries):
            try:
                # Get target repository
                target_repo_obj = self.g.get_repo(f"{self.org_name}/{target_repo}")
                
                # Get reference to the target branch
                try:
                    ref = target_repo_obj.get_git_ref(f"heads/{target_branch}")
                except GithubException:
                    # Branch doesn't exist, create it from the default branch
                    default_branch = target_repo_obj.default_branch
                    default_ref = target_repo_obj.get_git_ref(f"heads/{default_branch}")
                    ref = target_repo_obj.create_git_ref(
                        ref=f"refs/heads/{target_branch}",
                        sha=default_ref.object.sha
                    )
                
                # Get current commit - use get_git_commit() to get GitCommit with tree attribute
                commit = target_repo_obj.get_git_commit(ref.object.sha)
                
                # Read file content as binary
                with open(local_file_path, 'rb') as f:
                    file_content = f.read()
                
                # Create blob with binary content
                # For large files, we need to use the raw content approach
                blob = target_repo_obj.create_git_blob(
                    content=base64.b64encode(file_content).decode('utf-8'),
                    encoding='base64'
                )
                
                # Create tree element for the file
                tree_element = InputGitTreeElement(
                    path=remote_file_path,
                    mode='100644',  # Regular file
                    type='blob',
                    sha=blob.sha
                )
                
                # Create new tree - use commit.tree.sha to get the tree SHA
                tree = target_repo_obj.create_git_tree([tree_element], base_tree=commit.tree)
                
                # Create new commit - pass the GitCommit object for parent
                new_commit = target_repo_obj.create_git_commit(
                    commit_message,
                    tree,
                    [commit]
                )
                
                # Update branch reference
                ref.edit(new_commit.sha)
                
                return {
                    "success": True,
                    "commit_sha": new_commit.sha,
                    "commit_url": new_commit.html_url,
                    "message": f"Successfully committed {local_file_path} to {target_repo}/{target_branch}",
                    "file_size": os.path.getsize(local_file_path)
                }
                
            except GithubException as e:
                if e.status == 422 and "too_large" in str(e).lower():
                    # File is too large for the git data API, use LFS instead
                    return self._commit_using_lfs(
                        target_repo, target_branch, local_file_path, 
                        remote_file_path, commit_message
                    )
                else:
                    print(f"Attempt {attempt + 1} failed with GitHub API error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with exception: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return {
            "success": False,
            "error": f"All {max_retries} attempts failed to commit {local_file_path}",
            "file_path": local_file_path
        }

    def _commit_using_lfs(self, target_repo, target_branch, local_file_path, 
                         remote_file_path, commit_message):
        """
        Fallback method for very large files using Git LFS.
        This requires the repository to have LFS enabled.
        """
        try:
            # This is a simplified approach - in practice, you might need
            # to use the Git LFS API or a different approach
            target_repo_obj = self.g.get_repo(f"{self.org_name}/{target_repo}")
            
            # Create a temporary file with LFS pointer
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                # Create LFS pointer file content
                with open(local_file_path, 'rb') as f:
                    import hashlib
                    content = f.read()
                    oid = hashlib.sha256(content).hexdigest()
                    size = len(content)
                
                pointer_content = f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {size}\n"
                tmp.write(pointer_content)
                tmp_path = tmp.name
            
            # Upload the actual binary content to LFS
            lfs_upload_url = f"{self.base_url}/repos/{self.org_name}/{target_repo}/git-lfs/objects/{oid}"
            lfs_headers = {
                **self.headers,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(size)
            }
            
            with open(local_file_path, 'rb') as f:
                response = requests.put(lfs_upload_url, headers=lfs_headers, data=f)
            
            if response.status_code not in [200, 202]:
                return {
                    "success": False,
                    "error": f"LFS upload failed: {response.text}",
                    "status_code": response.status_code
                }
            
            # Now commit the pointer file
            with open(tmp_path, 'r') as f:
                pointer_content = f.read()
            
            os.unlink(tmp_path)
            
            # Use the regular commit method for the pointer file
            result = self.commit_to_repo(
                source_repo="",  # Not needed
                target_repo=target_repo,
                target_branch=target_branch,
                file_path=remote_file_path,
                file_content=pointer_content,
                commit_message=commit_message
            )
            
            if result['success']:
                result['message'] = f"Committed using LFS: {result['message']}"
                result['lfs_oid'] = oid
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"LFS commit failed: {str(e)}"
            }

    def commit_to_repo(self, source_repo, target_repo, target_branch, 
                      file_path, file_content, commit_message, 
                      file_mode="100644", file_type="blob"):
        """
        Commit a file to another repository and branch.
        (Existing method kept for compatibility)
        """
        try:
            # Get target repository
            target_repo_obj = self.g.get_repo(f"{self.org_name}/{target_repo}")
            
            # Get reference to the target branch
            ref = target_repo_obj.get_git_ref(f"heads/{target_branch}")
            
            # Get current commit
            commit = target_repo_obj.get_commit(ref.object.sha)
            
            # Create blob with new file content
            blob = target_repo_obj.create_git_blob(file_content, "utf-8")
            
            # Create tree element for the file
            tree_element = InputGitTreeElement(
                path=file_path,
                mode=file_mode,
                type=file_type,
                sha=blob.sha
            )
            
            # Create new tree
            tree = target_repo_obj.create_git_tree([tree_element], base_tree=commit.tree)
            
            # Create new commit
            new_commit = target_repo_obj.create_git_commit(
                commit_message,
                tree,
                [commit]
            )
            
            # Update branch reference
            ref.edit(new_commit.sha)
            
            return {
                "success": True,
                "commit_sha": new_commit.sha,
                "commit_url": new_commit.html_url,
                "message": f"Successfully committed to {target_repo}/{target_branch}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to commit to {target_repo}/{target_branch}"
            }

    def create_or_update_file(self, target_repo, target_branch, file_path, content, commit_message):
        """
        Simple method to create or update a file using REST API.
        (Existing method kept for compatibility)
        """
        url = f"{self.base_url}/repos/{self.org_name}/{target_repo}/contents/{file_path}"
        
        # Check if file exists to get its SHA
        response = requests.get(url, headers=self.headers, 
                              params={"ref": target_branch})
        
        data = {
            "message": commit_message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": target_branch
        }
        
        if response.status_code == 200:
            # File exists, include SHA for update
            data["sha"] = response.json()["sha"]
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "commit": response.json()["commit"],
                "message": f"File {file_path} updated in {target_repo}"
            }
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }

    def safe_commit(self, target_repo, target_branch, file_path, content, commit_message, max_retries=3):
        """
        Commit with retry logic and better error handling.
        (Existing method kept for compatibility)
        """
        for attempt in range(max_retries):
            try:
                result = self.create_or_update_file(
                    target_repo, target_branch, file_path, content, commit_message
                )
                
                if result['success']:
                    return result
                else:
                    print(f"Attempt {attempt + 1} failed: {result['error']}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with exception: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return {"success": False, "error": "All attempts failed"}
    
class GitHubLargeFileCommitter:
    def __init__(self, github_token, org_name, user_name, user_email):
        """
        Initialize with GitHub credentials.
        
        Args:
            github_token (str): GitHub PAT with repo permissions
            org_name (str): Organization name
            user_name (str): Git user name for commits
            user_email (str): Git user email for commits
        """
        self.github_token = github_token
        self.org_name = org_name
        self.user_name = user_name
        self.user_email = user_email

    def commit_large_files(self, target_repo, target_branch, files_to_commit, commit_message):
        """
        Commit large files using Git LFS and direct git operations.
        
        Args:
            target_repo (str): Target repository name
            target_branch (str): Target branch name
            files_to_commit (dict): {file_path: local_file_path} or {file_path: binary_data}
            commit_message (str): Commit message
            
        Returns:
            dict: Result of the operation
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            repo_dir = os.path.join(temp_dir, target_repo)
            
            # Clone the repository
            clone_url = f"https://{self.github_token}@github.com/{self.org_name}/{target_repo}.git"
            result = subprocess.run([
                'git', 'clone', '--branch', target_branch, 
                '--single-branch', clone_url, repo_dir
            ], capture_output=True, text=True, cwd=temp_dir)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Clone failed: {result.stderr}",
                    "step": "clone"
                }
            
            # Configure git
            subprocess.run(['git', 'config', 'user.name', self.user_name], 
                         cwd=repo_dir, check=True)
            subprocess.run(['git', 'config', 'user.email', self.user_email], 
                         cwd=repo_dir, check=True)
            
            # Initialize Git LFS if not already initialized
            lfs_tracked = self._setup_git_lfs(repo_dir, files_to_commit.keys())
            
            # Copy files to repository
            for repo_path, local_data in files_to_commit.items():
                target_path = os.path.join(repo_dir, repo_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                from pathlib import Path
                import pathlib
                if isinstance(local_data, (str, Path)) and os.path.exists(local_data):
                    # Local file path
                    shutil.copy2(local_data, target_path)
                else:
                    # Binary data
                    with open(target_path, 'wb') as f:
                        f.write(local_data)
            
            # Add and commit files
            subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
            
            # Check if there are changes to commit
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=repo_dir, capture_output=True, text=True)
            if not status_result.stdout.strip():
                return {"success": True, "message": "No changes to commit"}
            
            subprocess.run(['git', 'commit', '-m', commit_message], 
                         cwd=repo_dir, check=True)
            
            # Push changes
            push_result = subprocess.run(['git', 'push', 'origin', target_branch], 
                                       cwd=repo_dir, capture_output=True, text=True)
            
            if push_result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully committed {len(files_to_commit)} files to {target_repo}/{target_branch}",
                    "lfs_used": lfs_tracked
                }
            else:
                return {
                    "success": False,
                    "error": f"Push failed: {push_result.stderr}",
                    "step": "push"
                }
                
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git command failed: {e.stderr if hasattr(e, 'stderr') else str(e)}",
                "step": "git_command"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": "unknown"
            }
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _setup_git_lfs(self, repo_dir, file_paths):
        """Setup Git LFS for large files."""
        try:
            # Check if Git LFS is installed
            subprocess.run(['git', 'lfs', '--version'], 
                         cwd=repo_dir, capture_output=True, check=True)
            
            # Track common binary file patterns
            binary_extensions = {'.pkl', '.zip', '.gz', '.parquet', '.feather', '.h5'}
            lfs_tracked = False
            
            for file_path in file_paths:
                if any(file_path.endswith(ext) for ext in binary_extensions):
                    subprocess.run(['git', 'lfs', 'track', file_path], 
                                 cwd=repo_dir, capture_output=True)
                    lfs_tracked = True
            
            if lfs_tracked:
                # Add .gitattributes if LFS is being used
                subprocess.run(['git', 'add', '.gitattributes'], cwd=repo_dir)
            
            return lfs_tracked
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git LFS not available, continue without it
            return False

    def commit_large_binary_data(self, target_repo, target_branch, file_data_dict, commit_message):
        """
        Commit in-memory binary data as files.
        
        Args:
            file_data_dict (dict): {file_path: binary_data}

        Example : Commit large binary files:
            >>> committer = GitHubLargeFileCommitter(
            >>>     github_token="your_token",
            >>>     org_name="your-org",
            >>>     user_name="github-actions",
            >>>     user_email="actions@github.com"
            >>> )

        # Example : Commit from local files
            >>> result = committer.commit_large_files(
            >>> target_repo="data-repository",
            >>>    target_branch="main",
            >>>    files_to_commit={
            >>>        "data/stock_data.pkl": "/local/path/to/stock_data.pkl",
            >>>        "data/ticks.json.zip": "/local/path/to/ticks.json.zip"
            >>>    },
            >>>    commit_message="Add large binary data files"
            >>> )
                # Create binary data in memory
            >>>        stock_data = {"AAPL": [100, 101, 102], "GOOGL": [2000, 2001, 2002]}
            >>>        pickle_bytes = pickle.dumps(stock_data)

                # Create zip file in memory
            >>>        zip_buffer = io.BytesIO()
            >>>        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            >>>            zip_file.writestr('ticks.json', json.dumps({"data": "large json content"}))
            >>>        zip_bytes = zip_buffer.getvalue()

            >>>        result = committer.commit_large_binary_data(
            >>>            target_repo="data-repository",
            >>>            target_branch="main",
            >>>            file_data_dict={
            >>>                "data/stock_data.pkl": pickle_bytes,
            >>>                "data/ticks.json.zip": zip_bytes
            >>>            },
            >>>            commit_message="Add in-memory binary data files"
            >>>        )
        """
        return self.commit_large_files(target_repo, target_branch, file_data_dict, commit_message)

class GitHubLargeAssetCommitter:
    def __init__(self, github_token, org_name):
        self.github_token = github_token
        self.org_name = org_name
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.base_url = "https://api.github.com"

    def create_release_with_assets(self, target_repo, tag_name, assets, release_message):
        """
        Create a GitHub release with large binary assets.
        
        Args:
            target_repo (str): Target repository
            tag_name (str): Release tag name
            assets (dict): {asset_name: file_path_or_data}
            release_message (str): Release description
        """
        try:
            # Create release
            release_url = f"{self.base_url}/repos/{self.org_name}/{target_repo}/releases"
            release_data = {
                "tag_name": tag_name,
                "name": tag_name,
                "body": release_message,
                "draft": False,
                "prerelease": False
            }
            
            response = requests.post(release_url, headers=self.headers, json=release_data)
            if response.status_code != 201:
                return {"success": False, "error": f"Release creation failed: {response.text}"}
            
            release_id = response.json()["id"]
            upload_url = response.json()["upload_url"].replace("{?name,label}", "")
            
            # Upload assets
            uploaded_assets = []
            for asset_name, asset_data in assets.items():
                if isinstance(asset_data, (str, Path)) and os.path.exists(asset_data):
                    # Read from file
                    with open(asset_data, 'rb') as f:
                        file_content = f.read()
                else:
                    # Use binary data directly
                    file_content = asset_data
                
                # Upload asset
                asset_upload_url = f"{upload_url}?name={asset_name}"
                headers = self.headers.copy()
                headers["Content-Type"] = "application/octet-stream"
                
                asset_response = requests.post(asset_upload_url, headers=headers, data=file_content)
                if asset_response.status_code == 201:
                    uploaded_assets.append(asset_name)
                else:
                    print(f"Failed to upload {asset_name}: {asset_response.text}")
            
            return {
                "success": True,
                "release_id": release_id,
                "uploaded_assets": uploaded_assets,
                "release_url": response.json()["html_url"]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class HybridGitHubCommitter:
    def __init__(self, github_token, org_name, user_name, user_email):
        self.small_committer = GitHubCrossRepoCommitter(github_token, org_name)
        self.large_committer = GitHubLargeFileCommitter(github_token, org_name, user_name, user_email)
        self.release_committer = GitHubLargeAssetCommitter(github_token, org_name)

    def commit_hybrid(self, target_repo, target_branch, small_files, large_files, commit_message):
        """
        Commit small files via API and large files via Git LFS.
        
        # Example : Hybrid approach
            >>>        hybrid_committer = HybridGitHubCommitter(
            >>>            github_token="your_token",
            >>>            org_name="your-org",
            >>>            user_name="github-actions",
            >>>            user_email="actions@github.com"
            >>>        )

            >>>        result = hybrid_committer.commit_hybrid(
            >>>            target_repo="data-repository",
            >>>            target_branch="main",
            >>>            small_files={
            >>>                "metadata.json": '{"version": "1.0", "description": "Data update"}',
            >>>                "README.md": "# Data Files\nThis contains large binary files."
            >>>            },
            >>>            large_files={
            >>>                "data/large_file.pkl": pickle_bytes,
            >>>                "data/archive.zip": zip_bytes
            >>>            },
            >>>            commit_message="Mixed commit with small and large files"
            >>>        )
        """
        results = {}
        
        # Commit small files via API
        if small_files:
            small_files_data = []
            for path, content in small_files.items():
                if isinstance(content, str):
                    small_files_data.append({
                        "path": path,
                        "content": content,
                        "mode": "100644"
                    })
            
            if small_files_data:
                results["small_files"] = self.small_committer.commit_multiple_files(
                    target_repo, target_branch, small_files_data, commit_message
                )
        
        # Commit large files via Git LFS
        if large_files:
            results["large_files"] = self.large_committer.commit_large_files(
                target_repo, target_branch, large_files, commit_message
            )
        
        return results

    def commit_with_references(self, target_repo, target_branch, files, large_files_threshold_mb=10):
        """
        Commit files, using releases for very large files and storing references.
        """
        small_files = {}
        large_files = {}
        release_assets = {}
        
        for file_path, content in files.items():
            size_mb = len(content) / (1024 * 1024) if isinstance(content, bytes) else 0
            
            if size_mb > large_files_threshold_mb:
                # Very large file, use release
                release_assets[file_path] = content
            elif isinstance(content, bytes) or (isinstance(content, str) and len(content) > 1000000):
                # Large file, use Git LFS
                large_files[file_path] = content
            else:
                # Small file, use API
                small_files[file_path] = content.decode() if isinstance(content, bytes) else content
        
        results = {}
        
        # Commit small and large files
        if small_files or large_files:
            results["commit"] = self.commit_hybrid(
                target_repo, target_branch, small_files, large_files,
                "Automated commit with mixed file sizes"
            )
        
        # Create release for very large files
        if release_assets:
            tag_name = f"data-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            results["release"] = self.release_committer.create_release_with_assets(
                target_repo, tag_name, release_assets,
                "Automated data release with large files"
            )
            
            # Create a manifest file referencing the release
            if results["release"].get("success"):
                manifest = {
                    "release_tag": tag_name,
                    "release_url": results["release"]["release_url"],
                    "assets": list(release_assets.keys()),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Commit manifest file
                self.small_committer.create_or_update_file(
                    target_repo, target_branch,
                    "release_manifest.json",
                    json.dumps(manifest, indent=2),
                    "Add manifest for large file release"
                )
        
        return results
