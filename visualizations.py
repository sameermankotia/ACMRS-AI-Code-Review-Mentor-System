import streamlit as st
import pandas as pd
import altair as alt
from typing import Dict, List, Any
import pygments
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
import re

def render_annotated_code(code_content: str, issues: List[Dict[str, Any]], file_path: str) -> None:
    """
    Render code with annotations for issues.
    
    Args:
        code_content: The code content as a string
        issues: List of issues found in the code
        file_path: Path to the file
    """
    # Prepare the code for syntax highlighting
    try:
        lexer = get_lexer_for_filename(file_path)
    except:
        # Fallback to text if the lexer is not found
        lexer = get_lexer_by_name('text')
    
    formatter = HtmlFormatter(style='monokai')
    css = formatter.get_style_defs('.highlight')
    
    # Inject the CSS for syntax highlighting
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    
    # Group issues by line number
    issues_by_line = {}
    for issue in issues:
        line_num = issue.get("line", 0)
        if line_num not in issues_by_line:
            issues_by_line[line_num] = []
        issues_by_line[line_num].append(issue)
    
    # Split the code into lines for display
    lines = code_content.splitlines()
    
    # Display the code with line numbers and annotations
    st.markdown("### Code with Issues")
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Determine the background color based on issues
        bg_color = "transparent"
        if line_num in issues_by_line:
            # Get the highest severity for this line
            severities = [issue.get("severity", "info") for issue in issues_by_line[line_num]]
            highest_severity = max(severities, key=lambda s: {"error": 3, "warning": 2, "info": 1}.get(s, 0))
            
            if highest_severity == "error":
                bg_color = "rgba(255, 0, 0, 0.1)"
            elif highest_severity == "warning":
                bg_color = "rgba(255, 165, 0, 0.1)"
            else:
                bg_color = "rgba(0, 0, 255, 0.1)"
        
        # Highlight the line
        highlighted_line = pygments.highlight(line, lexer, formatter)
        
        # Display the line with line number in a flex container
        st.markdown(
            f'<div style="display: flex; background-color: {bg_color};">'
            f'<div style="width: 50px; text-align: right; padding-right: 10px; color: #888; user-select: none;">{line_num}</div>'
            f'<div style="flex-grow: 1;">{highlighted_line}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Display issues for this line
        if line_num in issues_by_line:
            with st.expander(f"{len(issues_by_line[line_num])} issue(s) found"):
                for issue in issues_by_line[line_num]:
                    severity = issue.get("severity", "info")
                    severity_color = {"error": "red", "warning": "orange", "info": "blue"}.get(severity, "blue")
                    
                    st.markdown(
                        f'<span style="color: {severity_color}; font-weight: bold;">{severity.upper()}</span>: '
                        f'{issue.get("message", "No description")}',
                        unsafe_allow_html=True
                    )
                    
                    # Display suggested fix if available
                    if "fix" in issue and issue["fix"]:
                        st.markdown(f"**Suggested fix:** {issue['fix']}")
                    
                    # Display source of the issue (static or LLM)
                    if "type" in issue:
                        st.markdown(f"**Source:** {issue['type'].upper()}")
                    
                    st.markdown("---")

def create_tech_debt_chart(tech_debt_scores: Dict[str, Dict[str, Any]]) -> alt.Chart:
    """
    Create a chart to visualize technical debt scores.
    
    Args:
        tech_debt_scores: Dictionary mapping filenames to debt scores
        
    Returns:
        Altair chart object
    """
    # Extract the scores for the chart
    chart_data = []
    for filename, data in tech_debt_scores.items():
        # Use just the filename without the full path
        short_name = filename.split('/')[-1]
        
        # Add the overall score
        chart_data.append({
            "File": short_name,
            "Score": data["overall"],
        })
    
    # Create the DataFrame
    df = pd.DataFrame(chart_data)
    
    # Sort by score in descending order
    df = df.sort_values("Score", ascending=False)
    
    # Create the chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Score", title="Technical Debt Score"),
        y=alt.Y("File", title="File", sort="-x"),
        color=alt.Color("Score", scale=alt.Scale(
            domain=[0, 50, 100],
            range=["green", "orange", "red"]
        )),
        tooltip=["File", "Score"]
    ).properties(
        title="Technical Debt by File",
        width="container",
        height=30 * len(df)  # Adjust height based on number of files
    )
    
    return chart

def create_issue_summary_chart(issues: List[Dict[str, Any]]) -> alt.Chart:
    """
    Create a chart to summarize issues by type and severity.
    
    Args:
        issues: List of issues found in the code
        
    Returns:
        Altair chart object
    """
    # Count issues by type and severity
    issue_counts = []
    
    # Count by type
    type_counts = {}
    for issue in issues:
        issue_type = issue.get("type", "unknown")
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
    
    for issue_type, count in type_counts.items():
        issue_counts.append({
            "Category": "Type",
            "Value": issue_type.capitalize(),
            "Count": count
        })
    
    # Count by severity
    severity_counts = {}
    for issue in issues:
        severity = issue.get("severity", "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    for severity, count in severity_counts.items():
        issue_counts.append({
            "Category": "Severity",
            "Value": severity.capitalize(),
            "Count": count
        })
    
    # Create the DataFrame
    df = pd.DataFrame(issue_counts)
    
    # Create the chart
    chart = alt.Chart(df).mark_bar().encode(
        x="Count",
        y=alt.Y("Value", sort="-x"),
        color="Value",
        row="Category",
        tooltip=["Value", "Count"]
    ).properties(
        width="container",
        height=150
    )
    
    return chart

def render_code_diff(before_content: str, after_content: str, file_path: str) -> None:
    """
    Render a side-by-side diff of code before and after changes.
    
    Args:
        before_content: The code content before changes
        after_content: The code content after changes
        file_path: Path to the file
    """
    # Prepare the code for syntax highlighting
    try:
        lexer = get_lexer_for_filename(file_path)
    except:
        # Fallback to text if the lexer is not found
        lexer = get_lexer_by_name('text')
    
    formatter = HtmlFormatter(style='monokai')
    css = formatter.get_style_defs('.highlight')
    
    # Inject the CSS for syntax highlighting
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    
    # Split the code into lines
    before_lines = before_content.splitlines()
    after_lines = after_content.splitlines()
    
    # Create two columns for side-by-side comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Before")
        
        for i, line in enumerate(before_lines):
            line_num = i + 1
            highlighted_line = pygments.highlight(line, lexer, formatter)
            
            st.markdown(
                f'<div style="display: flex;">'
                f'<div style="width: 30px; text-align: right; padding-right: 10px; color: #888; user-select: none;">{line_num}</div>'
                f'<div style="flex-grow: 1;">{highlighted_line}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown("### After")
        
        for i, line in enumerate(after_lines):
            line_num = i + 1
            highlighted_line = pygments.highlight(line, lexer, formatter)
            
            # Highlight changed lines
            bg_color = "transparent"
            if i < len(before_lines) and line != before_lines[i]:
                bg_color = "rgba(0, 255, 0, 0.1)"  # Light green for changes
            elif i >= len(before_lines):
                bg_color = "rgba(0, 0, 255, 0.1)"  # Light blue for new lines
            
            st.markdown(
                f'<div style="display: flex; background-color: {bg_color};">'
                f'<div style="width: 30px; text-align: right; padding-right: 10px; color: #888; user-select: none;">{line_num}</div>'
                f'<div style="flex-grow: 1;">{highlighted_line}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

def create_issue_heatmap(issues: List[Dict[str, Any]], files: List[str]) -> alt.Chart:
    """
    Create a heatmap of issues across files.
    
    Args:
        issues: List of issues found in the code
        files: List of file paths
        
    Returns:
        Altair chart object
    """
    # Count issues by file and severity
    heatmap_data = []
    
    for file in files:
        # Use just the filename without the full path
        short_name = file.split('/')[-1]
        
        # Count issues for this file
        error_count = sum(1 for issue in issues if issue.get("file") == file and issue.get("severity") == "error")
        warning_count = sum(1 for issue in issues if issue.get("file") == file and issue.get("severity") == "warning")
        info_count = sum(1 for issue in issues if issue.get("file") == file and issue.get("severity") == "info")
        
        # Add to the data
        heatmap_data.append({
            "File": short_name,
            "Severity": "Error",
            "Count": error_count
        })
        heatmap_data.append({
            "File": short_name,
            "Severity": "Warning",
            "Count": warning_count
        })
        heatmap_data.append({
            "File": short_name,
            "Severity": "Info",
            "Count": info_count
        })
    
    # Create the DataFrame
    df = pd.DataFrame(heatmap_data)
    
    # Create the heatmap
    chart = alt.Chart(df).mark_rect().encode(
        x="File",
        y="Severity",
        color=alt.Color("Count", scale=alt.Scale(scheme="orangered")),
        tooltip=["File", "Severity", "Count"]
    ).properties(
        title="Issue Distribution Across Files",
        width="container",
        height=200
    )
    
    return chart