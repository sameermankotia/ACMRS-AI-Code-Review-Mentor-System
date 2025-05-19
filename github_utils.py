import requests
import base64
from typing import Dict, List, Tuple, Any, Optional

def fetch_github_pr(repo: str, pr_number: str, github_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """
    Fetch pull request data from GitHub API.
    
    Args:
        repo: Repository in format 'owner/name'
        pr_number: Pull request number
        github_token: GitHub API token
        
    Returns:
        Tuple of (PR data, PR files)
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get PR details
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_response = requests.get(pr_url, headers=headers)
    
    if pr_response.status_code != 200:
        print(f"Error fetching PR: {pr_response.status_code} - {pr_response.text}")
        return None, None
    
    pr_data = pr_response.json()
    
    # Get PR files
    files_url = f"{pr_url}/files"
    files_response = requests.get(files_url, headers=headers)
    
    if files_response.status_code != 200:
        print(f"Error fetching PR files: {files_response.status_code} - {files_response.text}")
        return pr_data, None
    
    files_data = files_response.json()
    
    return pr_data, files_data

def get_file_content(repo: str, file_path: str, ref: str, github_token: str) -> Optional[str]:
    """
    Get file content from GitHub API.
    
    Args:
        repo: Repository in format 'owner/name'
        file_path: Path to the file
        ref: Git reference (branch, tag, or commit)
        github_token: GitHub API token
        
    Returns:
        File content as string
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching file content: {response.status_code} - {response.text}")
        return None
    
    try:
        content_data = response.json()
        
        # Check if the response is a file (not a directory)
        if isinstance(content_data, dict) and "content" in content_data:
            content = content_data["content"]
            # GitHub returns content as base64 encoded
            decoded_content = base64.b64decode(content).decode("utf-8")
            return decoded_content
        else:
            print(f"Response is not a file content: {content_data}")
            return None
    except Exception as e:
        print(f"Error decoding file content: {str(e)}")
        return None

def post_review_comment(repo: str, pr_number: str, commit_id: str, file_path: str, 
                       position: int, body: str, github_token: str) -> bool:
    """
    Post a review comment on a pull request.
    
    Args:
        repo: Repository in format 'owner/name'
        pr_number: Pull request number
        commit_id: Commit SHA to comment on
        file_path: Path to the file
        position: Line position in the diff
        body: Comment text
        github_token: GitHub API token
        
    Returns:
        True if successful, False otherwise
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
    
    data = {
        "commit_id": commit_id,
        "path": file_path,
        "position": position,
        "body": body
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        return True
    else:
        print(f"Error posting comment: {response.status_code} - {response.text}")
        return False

def get_repository_languages(repo: str, github_token: str) -> Dict[str, int]:
    """
    Get the languages used in a repository with their byte counts.
    
    Args:
        repo: Repository in format 'owner/name'
        github_token: GitHub API token
        
    Returns:
        Dictionary of language name to byte count
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{repo}/languages"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching repository languages: {response.status_code} - {response.text}")
        return {}
    
    return response.json()

def get_commit_history(repo: str, file_path: str, github_token: str, max_commits: int = 10) -> List[Dict[str, Any]]:
    """
    Get the commit history for a specific file.
    
    Args:
        repo: Repository in format 'owner/name'
        file_path: Path to the file
        github_token: GitHub API token
        max_commits: Maximum number of commits to retrieve
        
    Returns:
        List of commit data dictionaries
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{repo}/commits?path={file_path}&per_page={max_commits}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching commit history: {response.status_code} - {response.text}")
        return []
    
    commits = response.json()
    
    # Extract relevant information
    commit_history = []
    for commit in commits:
        commit_history.append({
            "sha": commit["sha"],
            "author": commit["commit"]["author"]["name"],
            "date": commit["commit"]["author"]["date"],
            "message": commit["commit"]["message"]
        })
    
    return commit_history