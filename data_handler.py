import json
import os
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Create data directory if it doesn't exist
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)

def save_feedback(feedback: Dict[str, Any]) -> bool:
    """
    Save developer feedback to file.
    
    Args:
        feedback: Dictionary containing feedback data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a unique filename based on repository and PR number
        repo = feedback.get("repository", "unknown").replace("/", "_")
        pr_number = feedback.get("pr_number", "0")
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        filename = f"feedback_{repo}_{pr_number}_{timestamp}.json"
        filepath = data_dir / filename
        
        # Save the feedback data
        with open(filepath, 'w') as f:
            json.dump(feedback, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving feedback: {str(e)}")
        return False

def save_analysis_results(repo: str, pr_number: str, results: Dict[str, Any]) -> bool:
    """
    Save analysis results to file.
    
    Args:
        repo: Repository name
        pr_number: Pull request number
        results: Analysis results
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a simplified version of the results to save
        # (exclude large code contents to save space)
        simplified_results = {
            "repo": repo,
            "pr_number": pr_number,
            "date": datetime.datetime.now().isoformat(),
            "issues": results.get("issues", []),
            "tech_debt_scores": results.get("tech_debt_scores", {}),
            "review_time": results.get("review_time", 0),
            "issue_count": len(results.get("issues", [])),
            "review_time_mins": results.get("review_time", 0) / 60
        }
        
        # Create a unique filename
        repo_sanitized = repo.replace("/", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        filename = f"analysis_{repo_sanitized}_{pr_number}_{timestamp}.json"
        filepath = data_dir / filename
        
        # Save the results
        with open(filepath, 'w') as f:
            json.dump(simplified_results, f, indent=2)
            
        # Also save to a summary file for quick loading
        save_analysis_summary(simplified_results)
        
        return True
    except Exception as e:
        print(f"Error saving analysis results: {str(e)}")
        return False

def save_analysis_summary(analysis: Dict[str, Any]) -> bool:
    """
    Save a summary of the analysis to a summary file.
    
    Args:
        analysis: Analysis data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        summary_file = data_dir / "analysis_summary.json"
        
        # Load existing summary if available
        summary_data = []
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
            except:
                summary_data = []
        
        # Create summary entry
        summary_entry = {
            "repo": analysis.get("repo", ""),
            "pr_number": analysis.get("pr_number", ""),
            "date": analysis.get("date", datetime.datetime.now().isoformat()),
            "issue_count": analysis.get("issue_count", 0),
            "review_time_mins": analysis.get("review_time_mins", 0),
            "tech_debt_avg": calculate_avg_tech_debt(analysis.get("tech_debt_scores", {}))
        }
        
        # Add to summary data
        summary_data.append(summary_entry)
        
        # Save updated summary
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error saving analysis summary: {str(e)}")
        return False

def calculate_avg_tech_debt(tech_debt_scores: Dict[str, Any]) -> float:
    """
    Calculate average technical debt from scores.
    
    Args:
        tech_debt_scores: Dictionary of technical debt scores
        
    Returns:
        Average score
    """
    if not tech_debt_scores:
        return 0.0
    
    total = sum(score.get("overall", 0) for score in tech_debt_scores.values())
    return total / len(tech_debt_scores)

def load_previous_analyses(repo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load previous analysis summaries, optionally filtered by repository.
    
    Args:
        repo: Repository name to filter by (optional)
        
    Returns:
        List of analysis summary entries
    """
    try:
        summary_file = data_dir / "analysis_summary.json"
        
        if not summary_file.exists():
            return []
        
        with open(summary_file, 'r') as f:
            summary_data = json.load(f)
        
        # Filter by repository if specified
        if repo:
            summary_data = [entry for entry in summary_data if entry.get("repo") == repo]
        
        # Sort by date
        summary_data.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return summary_data
    except Exception as e:
        print(f"Error loading previous analyses: {str(e)}")
        return []

def load_feedback(repo: Optional[str] = None, pr_number: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load saved feedback data, optionally filtered by repository and PR.
    
    Args:
        repo: Repository name to filter by (optional)
        pr_number: Pull request number to filter by (optional)
        
    Returns:
        List of feedback data
    """
    try:
        feedback_files = list(data_dir.glob("feedback_*.json"))
        
        if not feedback_files:
            return []
        
        feedback_data = []
        
        for file in feedback_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                # Apply filters if specified
                if repo and data.get("repository") != repo:
                    continue
                
                if pr_number and str(data.get("pr_number")) != str(pr_number):
                    continue
                
                feedback_data.append(data)
            except:
                # Skip files that can't be parsed
                continue
        
        # Sort by timestamp
        feedback_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return feedback_data
    except Exception as e:
        print(f"Error loading feedback: {str(e)}")
        return []

def get_detailed_analysis(repo: str, pr_number: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed analysis results for a specific PR.
    
    Args:
        repo: Repository name
        pr_number: Pull request number
        
    Returns:
        Detailed analysis data or None if not found
    """
    try:
        repo_sanitized = repo.replace("/", "_")
        analysis_files = list(data_dir.glob(f"analysis_{repo_sanitized}_{pr_number}_*.json"))
        
        if not analysis_files:
            return None
        
        # Get the most recent analysis
        latest_file = max(analysis_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error getting detailed analysis: {str(e)}")
        return None

def delete_old_data(days: int = 30) -> bool:
    """
    Delete data older than the specified number of days.
    
    Args:
        days: Number of days to keep data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Calculate the cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Find all JSON files in the data directory
        data_files = list(data_dir.glob("*.json"))
        
        for file in data_files:
            # Skip the summary file
            if file.name == "analysis_summary.json":
                continue
            
            # Check file modification time
            mod_time = datetime.datetime.fromtimestamp(file.stat().st_mtime)
            
            if mod_time < cutoff_date:
                # Delete the file
                file.unlink()
        
        # Update the summary file to remove old entries
        summary_file = data_dir / "analysis_summary.json"
        
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
            
            # Filter out old entries
            cutoff_str = cutoff_date.isoformat()
            summary_data = [entry for entry in summary_data if entry.get("date", "") >= cutoff_str]
            
            # Save updated summary
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error deleting old data: {str(e)}")
        return False