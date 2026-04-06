import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple
import os
from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes import Archiver


class GitHubCommitFetcher:
    """
    A class to fetch commits and files from GitHub repositories within a specified time window.
    
    Usage:
        fetcher = GitHubCommitFetcher()
        
        # Get latest commit info
        commit_info = fetcher.get_latest_commit_in_window(
            file_path="pkbrokers/kite/examples/results/Data/ticks.json",
            start_ist="09:40:00",
            end_ist="09:50:00"
        )
        
        # Download the file
        fetcher.download_file(commit_info["sha"], output_path="/path/to/save/ticks.json")
        
        # Or do both at once
        success, file_path = fetcher.fetch_latest_file_in_window(
            file_path="pkbrokers/kite/examples/results/Data/ticks.json",
            start_ist="09:40:00",
            end_ist="09:50:00",
            output_path="/path/to/save/ticks.json"
        )
    """
    
    def __init__(self, owner: str = "pkjmesra", repo: str = "PKBrokers", 
                 branch: str = "main", github_token: Optional[str] = None):
        """
        Initialize the GitHubCommitFetcher.
        
        Args:
            owner: GitHub repository owner
            repo: Repository name
            branch: Branch name (default: "main")
            github_token: GitHub personal access token (optional but recommended)
        """
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.github_token = github_token or PKEnvironment().GITHUB_TOKEN
        self.ist_offset = timedelta(hours=5, minutes=30)
        
    def _ist_to_utc(self, date_str: str, time_str: str) -> datetime:
        """
        Convert IST datetime string to UTC datetime object.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM:SS format (24-hour)
            
        Returns:
            UTC datetime object
        """
        dt_ist = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        dt_utc = dt_ist - self.ist_offset
        return dt_utc.replace(tzinfo=timezone.utc)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication if token is provided."""
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers
    
    def get_commits_in_window(
        self,
        file_path: str,
        start_ist: str,
        end_ist: str,
        target_date: Optional[str] = None,
        per_page: int = 100
    ) -> List[Dict]:
        """
        Get all commits for a file within a specified IST time window.
        
        Args:
            file_path: Path to the file in the repository
            start_ist: Start time in IST (HH:MM:SS format)
            end_ist: End time in IST (HH:MM:SS format)
            target_date: Date in YYYY-MM-DD format (defaults to today)
            per_page: Number of commits per API page (max 100)
            
        Returns:
            List of commit dictionaries with keys: sha, date, message, author, url
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        start_utc = self._ist_to_utc(target_date, start_ist)
        end_utc = self._ist_to_utc(target_date, end_ist)
        
        print(f"🔍 Looking for commits between IST {start_ist} - {end_ist} on {target_date}")
        print(f"   UTC window: {start_utc.isoformat()} to {end_utc.isoformat()}")
        
        headers = self._get_headers()
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        params = {
            "path": file_path,
            "sha": self.branch,
            "per_page": per_page
        }
        
        all_commits = []
        page = 1
        window_commits = []
        
        # Paginate through all commits
        while True:
            params["page"] = page
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"❌ API error: {response.status_code}")
                break
            
            commits = response.json()
            if not commits:
                break
            
            all_commits.extend(commits)
            page += 1
            
            # Stop if we've gone back far enough
            oldest_date = datetime.fromisoformat(
                commits[-1]["commit"]["committer"]["date"].replace('Z', '+00:00')
            )
            if oldest_date < start_utc:
                break
        
        print(f"📊 Fetched {len(all_commits)} total commits for {file_path}")
        
        # Find commits within the time window
        for commit in all_commits:
            committer_date = datetime.fromisoformat(
                commit["commit"]["committer"]["date"].replace('Z', '+00:00')
            )
            
            if start_utc <= committer_date <= end_utc:
                window_commits.append({
                    "sha": commit["sha"],
                    "date": committer_date,
                    "message": commit["commit"]["message"].strip(),
                    "author": commit["commit"]["author"]["name"],
                    "url": commit["html_url"]
                })
        
        return window_commits
    
    def get_latest_commit_in_window(
        self,
        file_path: str,
        start_ist: str,
        end_ist: str,
        target_date: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get the latest commit for a file within a specified IST time window.
        
        Args:
            file_path: Path to the file in the repository
            start_ist: Start time in IST (HH:MM:SS format)
            end_ist: End time in IST (HH:MM:SS format)
            target_date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Commit dictionary or None if no commit found
        """
        commits = self.get_commits_in_window(file_path, start_ist, end_ist, target_date)
        
        if not commits:
            print(f"❌ No commits found in the specified time window.")
            return None
        
        # Display all commits found
        print(f"\n📋 Found {len(commits)} commit(s) in the time window:")
        print("=" * 80)
        for i, commit_info in enumerate(commits, 1):
            ist_time = (commit_info["date"] + self.ist_offset).time()
            print(f"{i}. Commit: {commit_info['sha'][:7]}")
            print(f"   Time (IST): {ist_time}")
            print(f"   Time (UTC): {commit_info['date']}")
            print(f"   Author: {commit_info['author']}")
            print(f"   Message: {commit_info['message']}")
            print(f"   URL: {commit_info['url']}")
            print()
        
        # Return the latest commit (first in the list)
        latest = commits[0]
        print("=" * 80)
        print(f"✅ LATEST COMMIT IN WINDOW:")
        print(f"   SHA: {latest['sha'][:7]}")
        print(f"   Time (IST): {(latest['date'] + self.ist_offset).time()}")
        print(f"   Message: {latest['message']}")
        print()
        
        return latest
    
    def download_file(
        self,
        commit_sha: str,
        file_path: str,
        output_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Download a file from a specific commit.
        
        Args:
            commit_sha: Commit SHA hash
            file_path: Path to the file in the repository
            output_path: Path to save the file (defaults to user data dir with original filename)
            
        Returns:
            Tuple of (success, output_path)
        """
        raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{commit_sha}/{file_path}"
        
        if output_path is None:
            filename = os.path.basename(file_path)
            output_path = os.path.join(Archiver.get_user_data_dir(), filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"📥 Downloading from {raw_url} ...")
        
        try:
            response = requests.get(raw_url, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Saved as {output_path}")
                return True, output_path
            else:
                print(f"❌ Failed to download file: HTTP {response.status_code}")
                return False, None
        except Exception as e:
            print(f"❌ Error downloading file: {e}")
            return False, None
    
    def fetch_latest_file_in_window(
        self,
        file_path: str,
        start_ist: str,
        end_ist: str,
        target_date: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Fetch the latest version of a file committed within the specified time window.
        
        Args:
            file_path: Path to the file in the repository
            start_ist: Start time in IST (HH:MM:SS format)
            end_ist: End time in IST (HH:MM:SS format)
            target_date: Date in YYYY-MM-DD format (defaults to today)
            output_path: Path to save the file (defaults to user data dir)
            
        Returns:
            Tuple of (success, output_path, commit_info)
        """
        # Get the latest commit in the window
        commit_info = self.get_latest_commit_in_window(
            file_path, start_ist, end_ist, target_date
        )
        
        if not commit_info:
            return False, None, None
        
        # Download the file
        success, saved_path = self.download_file(
            commit_info["sha"], file_path, output_path
        )
        
        return success, saved_path, commit_info


# Convenience function for backward compatibility
def fetch_ticks_json_in_window(
    start_ist: str = "09:40:00",
    end_ist: str = "09:50:00",
    target_date: Optional[str] = None,
    output_path: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Convenience function to fetch ticks.json committed within a time window.
    
    Args:
        start_ist: Start time in IST (HH:MM:SS format)
        end_ist: End time in IST (HH:MM:SS format)
        target_date: Date in YYYY-MM-DD format (defaults to today)
        output_path: Path to save the file (defaults to user data dir)
        
    Returns:
        Tuple of (success, output_path, commit_info)
    """
    fetcher = GitHubCommitFetcher()
    return fetcher.fetch_latest_file_in_window(
        file_path="pkbrokers/kite/examples/results/Data/ticks.json",
        start_ist=start_ist,
        end_ist=end_ist,
        target_date=target_date,
        output_path=output_path
    )


# Example usage if run directly
# if __name__ == "__main__":
#     # Example 1: Using the class directly
#     fetcher = GitHubCommitFetcher()
    
    # # Get commits for ticks.json between 9:40 AM and 9:50 AM IST today
    # commits = fetcher.get_commits_in_window(
    #     file_path="pkbrokers/kite/examples/results/Data/ticks.json",
    #     start_ist="09:40:00",
    #     end_ist="09:50:00"
    # )
    
    # # Download the latest file
    # if commits:
    #     success, path, commit = fetcher.fetch_latest_file_in_window(
    #         file_path="pkbrokers/kite/examples/results/Data/ticks.json",
    #         start_ist="09:40:00",
    #         end_ist="09:50:00"
    #     )
    
    # Example 2: Using the convenience function
    success, file_path, commit_info = fetch_ticks_json_in_window()
    
    # Example 3: Custom parameters
    # success, file_path, commit_info = fetcher.fetch_latest_file_in_window(
    #     file_path="custom/path/to/file.json",
    #     start_ist="10:00:00",
    #     end_ist="10:15:00",
    #     target_date="2026-04-05",
    #     output_path="/custom/output/path/file.json"
    # )
    # for commit in commit_info:
    # print(f"SHA: {commit_info['sha'][:7]}, Time: {commit_info['date']}, Message: {commit_info['message']}")