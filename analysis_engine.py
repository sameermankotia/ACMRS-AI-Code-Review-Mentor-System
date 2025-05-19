import os
import re
import json
import tempfile
import subprocess
from typing import Dict, List, Tuple, Any, Optional
import requests

def run_static_analysis(code_content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Run static analysis on code content.
    
    Args:
        code_content: The code content as a string
        file_path: Path to the file
        
    Returns:
        List of issues found
    """
    issues = []
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Create a temporary file to write the code
    with tempfile.NamedTemporaryFile(suffix=file_extension, mode='w+', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code_content)
    
    try:
        # Python static analysis
        if file_extension == '.py':
            # Run pylint
            try:
                cmd = ["pylint", "--output-format=json", temp_file_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.stdout:
                    pylint_issues = json.loads(result.stdout)
                    for issue in pylint_issues:
                        issues.append({
                            "line": issue.get("line", 0),
                            "column": issue.get("column", 0),
                            "message": issue.get("message", ""),
                            "severity": map_pylint_severity(issue.get("type", "")),
                            "rule": issue.get("symbol", "")
                        })
            except Exception as e:
                print(f"Error running pylint: {str(e)}")
            
            # Run flake8
            try:
                cmd = ["flake8", "--format=json", temp_file_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.stdout:
                    flake8_issues = json.loads(result.stdout)
                    for _, issue in flake8_issues.items():
                        issues.append({
                            "line": issue.get("line_number", 0),
                            "column": issue.get("column_number", 0),
                            "message": issue.get("text", ""),
                            "severity": "warning",
                            "rule": issue.get("code", "")
                        })
            except Exception as e:
                print(f"Error running flake8: {str(e)}")
        
        # JavaScript/TypeScript static analysis
        elif file_extension in ['.js', '.jsx', '.ts', '.tsx']:
            # Run ESLint if available
            try:
                cmd = ["eslint", "--format=json", temp_file_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.stdout:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        for message in file_result.get("messages", []):
                            issues.append({
                                "line": message.get("line", 0),
                                "column": message.get("column", 0),
                                "message": message.get("message", ""),
                                "severity": "error" if message.get("severity", 1) == 2 else "warning",
                                "rule": message.get("ruleId", "")
                            })
            except Exception as e:
                print(f"Error running eslint: {str(e)}")
        
        # Fallback to basic pattern matching for all file types
        issues.extend(basic_pattern_analysis(code_content, file_extension))
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass
    
    return issues

def map_pylint_severity(pylint_type: str) -> str:
    """Map pylint message type to severity level."""
    if pylint_type in ["error", "fatal"]:
        return "error"
    elif pylint_type in ["warning", "refactor"]:
        return "warning"
    else:
        return "info"

def basic_pattern_analysis(code_content: str, file_extension: str) -> List[Dict[str, Any]]:
    """
    Run basic pattern matching for common code issues.
    
    Args:
        code_content: The code content as a string
        file_extension: File extension (with leading dot)
        
    Returns:
        List of issues found
    """
    issues = []
    lines = code_content.splitlines()
    
    # Check line length
    max_line_length = 100
    for i, line in enumerate(lines):
        if len(line) > max_line_length:
            issues.append({
                "line": i + 1,
                "column": max_line_length + 1,
                "message": f"Line too long ({len(line)}/{max_line_length})",
                "severity": "info",
                "rule": "line-length"
            })
    
    # Check for TODO/FIXME comments
    todo_pattern = re.compile(r'\b(TODO|FIXME)\b', re.IGNORECASE)
    for i, line in enumerate(lines):
        if todo_pattern.search(line):
            issues.append({
                "line": i + 1,
                "column": 1,
                "message": "TODO or FIXME comment found",
                "severity": "info",
                "rule": "todo-comment"
            })
    
    # Check for hardcoded credentials
    credential_pattern = re.compile(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)
    for i, line in enumerate(lines):
        if credential_pattern.search(line):
            issues.append({
                "line": i + 1,
                "column": 1,
                "message": "Possible hardcoded credential found",
                "severity": "error",
                "rule": "hardcoded-credential"
            })
    
    # Check for empty catch blocks
    if file_extension in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java']:
        empty_catch_pattern = re.compile(r'catch\s*\([^)]*\)\s*{\s*}')
        code_without_newlines = ' '.join(lines)
        if empty_catch_pattern.search(code_without_newlines):
            issues.append({
                "line": 1,  # Can't determine exact line
                "column": 1,
                "message": "Empty catch block found",
                "severity": "warning",
                "rule": "empty-catch"
            })
    
    return issues

def run_llm_analysis(code_content: str, file_path: str, openai_api_key: str) -> List[Dict[str, Any]]:
    """
    Run LLM-based analysis on code content.
    
    Args:
        code_content: The code content as a string
        file_path: Path to the file
        openai_api_key: OpenAI API key
        
    Returns:
        List of issues found
    """
    # Skip very large files
    if len(code_content) > 10000:  # ~10KB limit
        return [{
            "line": 1,
            "message": "File too large for LLM analysis",
            "severity": "info",
            "fix": "Consider breaking the file into smaller modules"
        }]
    
    # Prepare the API request
    file_extension = os.path.splitext(file_path)[1].lower()
    language = get_language_from_extension(file_extension)
    
    # Create a prompt for the LLM
    prompt = f"""
    You are an expert code reviewer specializing in {language} development.
    Analyze the following code for potential issues:
    
    1. Bugs and logical errors
    2. Maintainability issues
    3. Performance concerns
    4. Security vulnerabilities
    5. Best practice violations
    
    For each issue, provide:
    - Line number
    - Brief description of the issue
    - Severity (error, warning, info)
    - Suggested fix
    
    Respond with a JSON array of issues, with each issue having the fields: "line", "message", "severity", and "fix".
    Only include actual issues - do not make up problems if the code looks good.
    
    CODE:
    ```{language}
    {code_content}
    ```
    """
    
    # Make the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are an expert code reviewer."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1500
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            print(f"Error from OpenAI API: {response.status_code} - {response.text}")
            return []
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON array from response (sometimes it includes explanation text)
        json_match = re.search(r'\[\s*{[^]]*}\s*\]', content, re.DOTALL)
        if json_match:
            issues_json = json_match.group(0)
        else:
            issues_json = content
        
        # Parse the JSON response
        try:
            issues = json.loads(issues_json)
            return issues
        except json.JSONDecodeError:
            print(f"Error parsing LLM response as JSON: {issues_json}")
            return []
            
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return []

def get_language_from_extension(file_extension: str) -> str:
    """Map file extension to language name."""
    extension_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript (React)',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript (React)',
        '.java': 'Java',
        '.c': 'C',
        '.cpp': 'C++',
        '.cs': 'C#',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sql': 'SQL',
    }
    
    return extension_map.get(file_extension.lower(), 'Unknown')

def calculate_tech_debt_score(code_content: str, file_path: str, issues: List[Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
    """
    Calculate a technical debt score based on static analysis and other metrics.
    
    Args:
        code_content: The code content as a string
        file_path: Path to the file
        issues: List of issues found by analysis
        
    Returns:
        Tuple of (overall_score, detailed_breakdown)
    """
    # Initialize debt score categories
    debt_details = {
        "complexity": 0.0,
        "duplication": 0.0,
        "documentation": 0.0,
        "code_smells": 0.0,
        "test_coverage": 0.0
    }
    
    lines = code_content.splitlines()
    total_lines = len(lines)
    
    # Skip empty files
    if total_lines == 0:
        return 0.0, debt_details
    
    # Calculate complexity score based on various metrics
    
    # 1. Complexity: based on indentation and function length
    max_indentation = 0
    function_lines = 0
    in_function = False
    function_count = 0
    
    for line in lines:
        # Check indentation level
        stripped = line.lstrip()
        if stripped:  # Non-empty line
            indentation = len(line) - len(stripped)
            max_indentation = max(max_indentation, indentation)
        
        # Count function lines (very basic detection)
        if re.match(r'^\s*(def|function|class|interface)\s+\w+', line):
            in_function = True
            function_count += 1
            function_lines = 1
        elif in_function:
            function_lines += 1
            if line.strip() == '}' or re.match(r'^\s*return\s', line):
                in_function = False
    
    # Calculate complexity scores
    avg_indentation = max_indentation / 4  # Normalize to 0-5 range approximately
    complexity_score = min(100, (avg_indentation * 20) + (function_lines / max(1, function_count) / 5))
    debt_details["complexity"] = complexity_score
    
    # 2. Duplication: check for repeated lines
    line_hash = {}
    duplicate_count = 0
    
    for line in lines:
        line_stripped = line.strip()
        if len(line_stripped) > 10:  # Ignore short lines
            if line_stripped in line_hash:
                duplicate_count += 1
            else:
                line_hash[line_stripped] = True
    
    duplication_score = min(100, (duplicate_count / max(1, total_lines)) * 200)  # Normalize to 0-100
    debt_details["duplication"] = duplication_score
    
    # 3. Documentation: comments and docstrings
    comment_lines = 0
    has_docstring = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check for various comment formats
        if line_stripped.startswith('#') or line_stripped.startswith('//') or line_stripped.startswith('/*'):
            comment_lines += 1
        # Check for docstrings (Python)
        if line_stripped.startswith('"""') or line_stripped.startswith("'''"):
            has_docstring = True
    
    comment_ratio = comment_lines / max(1, total_lines)
    documentation_score = min(100, (1 - comment_ratio) * 100)
    if has_docstring:
        documentation_score *= 0.7  # Reduce score if docstrings are present
    
    debt_details["documentation"] = documentation_score
    
    # 4. Code smells: based on analysis issues
    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    info_count = sum(1 for issue in issues if issue.get("severity") == "info")
    
    # Weight different severities
    weighted_issues = (error_count * 5 + warning_count * 2 + info_count) / max(1, total_lines) * 100
    code_smells_score = min(100, weighted_issues)
    debt_details["code_smells"] = code_smells_score
    
    # 5. Test coverage: heuristic based on filename and content
    test_coverage_score = 50  # Default score
    
    # Check if this is a test file
    if 'test' in file_path.lower() or 'spec' in file_path.lower():
        test_coverage_score = 0  # Test files don't have test debt
    else:
        # Check for import of test frameworks
        test_frameworks = ['unittest', 'pytest', 'jest', 'mocha', 'test']
        for framework in test_frameworks:
            if framework in code_content.lower():
                test_coverage_score = 30  # Reduce score if testing is mentioned
                break
    
    debt_details["test_coverage"] = test_coverage_score
    
    # Calculate overall score as weighted average
    weights = {
        "complexity": 0.25,
        "duplication": 0.20,
        "documentation": 0.15,
        "code_smells": 0.25,
        "test_coverage": 0.15
    }
    
    overall_score = sum(debt_details[key] * weights[key] for key in weights)
    
    return overall_score, debt_details