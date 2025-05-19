import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import time

# Import custom modules
from github_utils import fetch_github_pr, get_file_content
from analysis_engine import run_static_analysis, run_llm_analysis, calculate_tech_debt_score
from visualizations import render_annotated_code, create_tech_debt_chart, create_issue_summary_chart
from data_handler import save_feedback, save_analysis_results, load_previous_analyses

# Create data directory if it doesn't exist
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)

# App configuration
st.set_page_config(
    page_title="AI-Augmented Code Review Assistant",
    page_icon="🔍",
    layout="wide"
)

# Application state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_repo' not in st.session_state:
    st.session_state.current_repo = None
if 'current_pr' not in st.session_state:
    st.session_state.current_pr = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'feedback_submitted' not in st.session_state:
    st.session_state.feedback_submitted = False
if 'review_start_time' not in st.session_state:
    st.session_state.review_start_time = None

# App title and description
st.title("AI-Augmented Code Review Assistant")
st.markdown("""
This tool enhances the code review process by combining multiple AI models with human oversight.
It detects potential issues, identifies technical debt, and provides actionable suggestions while
preserving developer agency in the review process.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # API Token
    if not st.session_state.authenticated:
        github_token = st.text_input("GitHub API Token", type="password")
        if st.button("Authenticate"):
            if github_token:
                # Store token securely in session state
                st.session_state.github_token = github_token
                st.session_state.authenticated = True
                st.success("Authentication successful!")
            else:
                st.error("Please enter a GitHub token")
    else:
        st.success("Authenticated ✅")
        
        # Repository and PR selection
        repo = st.text_input("Repository (owner/name)", "microsoft/vscode")
        pr_number = st.text_input("Pull Request Number", "193075")
        
        # OpenAI API key for LLM analysis
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        
        # Analysis configuration
        st.header("Analysis Configuration")
        
        use_static = st.checkbox("Static Analysis", value=True)
        use_llm = st.checkbox("LLM Analysis", value=True, 
                           help="Uses OpenAI API to analyze code semantically")
        use_security = st.checkbox("Security Analysis", value=True)
        
        # Run analysis button
        if st.button("Run Analysis"):
            if repo and pr_number and (use_static or use_llm or use_security):
                if use_llm and not openai_api_key:
                    st.error("Please enter OpenAI API key for LLM analysis")
                else:
                    # Record start time for metrics
                    st.session_state.review_start_time = time.time()
                    
                    # Store configuration
                    st.session_state.current_repo = repo
                    st.session_state.current_pr = pr_number
                    st.session_state.use_static = use_static
                    st.session_state.use_llm = use_llm
                    st.session_state.use_security = use_security
                    if openai_api_key:
                        st.session_state.openai_api_key = openai_api_key
                    
                    # Reset analysis results and feedback
                    st.session_state.analysis_results = None
                    st.session_state.feedback_submitted = False
            else:
                st.error("Please enter repository and PR number, and select at least one analysis type")

# Main content area
if not st.session_state.authenticated:
    st.info("Please authenticate using your GitHub token to get started.")
elif not st.session_state.current_repo or not st.session_state.current_pr:
    st.info("Please configure a repository and pull request to analyze.")
else:
    # Display tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Code Review", "Technical Debt", "Metrics", "Feedback"])
    
    # Run analysis if not already done
    if st.session_state.analysis_results is None:
        with st.spinner("Running AI analysis on the pull request..."):
            try:
                # Fetch PR data
                pr_data, files_data = fetch_github_pr(
                    st.session_state.current_repo, 
                    st.session_state.current_pr,
                    st.session_state.github_token
                )
                
                if not pr_data or not files_data:
                    st.error("Failed to fetch PR data. Please check repository and PR number.")
                    st.stop()
                
                # Process each file in the PR
                all_issues = []
                tech_debt_scores = {}
                code_contents = {}
                
                for file in files_data:
                    filename = file["filename"]
                    
                    # Skip very large files and binaries
                    if file.get("changes", 0) > 1000 or not file.get("patch"):
                        continue
                    
                    # Check if file has a supported extension
                    supported_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', '.c', '.cpp', '.cs']
                    if not any(filename.endswith(ext) for ext in supported_extensions):
                        continue
                    
                    # Get file content
                    content = get_file_content(
                        st.session_state.current_repo,
                        filename,
                        pr_data["head"]["ref"],
                        st.session_state.github_token
                    )
                    
                    if content:
                        code_contents[filename] = content
                        file_issues = []
                        
                        # Run static analysis if enabled
                        if st.session_state.use_static:
                            static_results = run_static_analysis(content, filename)
                            file_issues.extend([{
                                "file": filename,
                                "type": "static",
                                "line": issue.get("line", 0),
                                "message": issue.get("message", ""),
                                "severity": issue.get("severity", "info")
                            } for issue in static_results])
                        
                        # Run LLM analysis if enabled
                        if st.session_state.use_llm and hasattr(st.session_state, 'openai_api_key'):
                            llm_results = run_llm_analysis(content, filename, st.session_state.openai_api_key)
                            file_issues.extend([{
                                "file": filename,
                                "type": "llm",
                                "line": issue.get("line", 0),
                                "message": issue.get("message", ""),
                                "severity": issue.get("severity", "info"),
                                "suggested_fix": issue.get("fix", "")
                            } for issue in llm_results])
                        
                        # Calculate technical debt score
                        tech_debt, debt_details = calculate_tech_debt_score(content, filename, file_issues)
                        tech_debt_scores[filename] = {
                            "overall": tech_debt,
                            "details": debt_details
                        }
                        
                        # Add to all issues
                        all_issues.extend(file_issues)
                
                # Calculate review time
                review_time = time.time() - st.session_state.review_start_time
                
                # Store results in session state
                st.session_state.analysis_results = {
                    "pr_data": pr_data,
                    "files_data": files_data,
                    "issues": all_issues,
                    "tech_debt_scores": tech_debt_scores,
                    "code_contents": code_contents,
                    "review_time": review_time
                }
                
                # Save analysis results to file
                save_analysis_results(
                    st.session_state.current_repo,
                    st.session_state.current_pr,
                    st.session_state.analysis_results
                )
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.stop()
    
    # Tab 1: Code Review
    with tab1:
        st.header("Code Review")
        
        results = st.session_state.analysis_results
        
        # File selection dropdown
        file_list = list(results["code_contents"].keys())
        if file_list:
            selected_file = st.selectbox("Select File to Review", file_list)
            
            # Get file content and issues
            code_content = results["code_contents"][selected_file]
            file_issues = [issue for issue in results["issues"] if issue["file"] == selected_file]
            
            # Render code with annotations
            render_annotated_code(code_content, file_issues, selected_file)
            
            # Issue summary
            st.subheader("Issue Summary")
            if file_issues:
                # Create a DataFrame for the issues
                issue_df = pd.DataFrame(file_issues)
                
                # Display issue counts by type and severity
                col1, col2 = st.columns(2)
                
                with col1:
                    type_counts = issue_df["type"].value_counts().reset_index()
                    type_counts.columns = ["Type", "Count"]
                    
                    type_chart = alt.Chart(type_counts).mark_bar().encode(
                        x="Type",
                        y="Count",
                        color="Type"
                    ).properties(
                        title="Issues by Type",
                        width=300
                    )
                    
                    st.altair_chart(type_chart, use_container_width=True)
                
                with col2:
                    severity_counts = issue_df["severity"].value_counts().reset_index()
                    severity_counts.columns = ["Severity", "Count"]
                    
                    severity_chart = alt.Chart(severity_counts).mark_bar().encode(
                        x="Severity",
                        y="Count",
                        color=alt.Color("Severity", scale=alt.Scale(
                            domain=["error", "warning", "info"],
                            range=["red", "orange", "blue"]
                        ))
                    ).properties(
                        title="Issues by Severity",
                        width=300
                    )
                    
                    st.altair_chart(severity_chart, use_container_width=True)
                
                # Display issue table with filtering
                st.subheader("Issues")
                
                # Add filters
                col1, col2 = st.columns(2)
                with col1:
                    severity_filter = st.multiselect(
                        "Filter by Severity",
                        options=issue_df["severity"].unique(),
                        default=issue_df["severity"].unique()
                    )
                
                with col2:
                    type_filter = st.multiselect(
                        "Filter by Type",
                        options=issue_df["type"].unique(),
                        default=issue_df["type"].unique()
                    )
                
                # Apply filters
                filtered_issues = issue_df[
                    issue_df["severity"].isin(severity_filter) & 
                    issue_df["type"].isin(type_filter)
                ]
                
                # Display filtered issues
                if not filtered_issues.empty:
                    st.dataframe(
                        filtered_issues[["line", "type", "severity", "message"]],
                        use_container_width=True
                    )
                else:
                    st.info("No issues match the selected filters.")
            else:
                st.info("No issues found in this file.")
        else:
            st.info("No files available for review.")
    
    # Tab 2: Technical Debt
    with tab2:
        st.header("Technical Debt Analysis")
        
        results = st.session_state.analysis_results
        tech_debt_scores = results["tech_debt_scores"]
        
        if tech_debt_scores:
            # Calculate overall tech debt score
            overall_score = sum(score["overall"] for score in tech_debt_scores.values()) / len(tech_debt_scores)
            
            st.metric(
                "Overall Technical Debt Score", 
                f"{overall_score:.1f}/100", 
                delta=None,
                help="Higher score indicates more technical debt"
            )
            
            # Technical debt chart
            tech_debt_chart = create_tech_debt_chart(tech_debt_scores)
            st.altair_chart(tech_debt_chart, use_container_width=True)
            
            # Detailed breakdown
            st.subheader("Technical Debt Breakdown")
            
            # Create data for detailed breakdown
            breakdown_data = []
            categories = set()
            
            for filename, data in tech_debt_scores.items():
                for category, score in data["details"].items():
                    breakdown_data.append({
                        "File": filename.split("/")[-1],  # Just the filename without path
                        "Category": category.replace("_", " ").title(),
                        "Score": score
                    })
                    categories.add(category)
            
            if breakdown_data:
                breakdown_df = pd.DataFrame(breakdown_data)
                
                # Create a grouped bar chart
                breakdown_chart = alt.Chart(breakdown_df).mark_bar().encode(
                    x="File",
                    y="Score",
                    color="Category",
                    tooltip=["File", "Category", "Score"]
                ).properties(
                    height=400
                )
                
                st.altair_chart(breakdown_chart, use_container_width=True)
                
                # Recommendations based on debt
                st.subheader("Recommendations")
                
                # Find the highest debt category
                avg_by_category = breakdown_df.groupby("Category")["Score"].mean()
                highest_category = avg_by_category.idxmax()
                highest_score = avg_by_category.max()
                
                # Provide recommendations
                if highest_score > 70:
                    st.warning(f"⚠️ Critical: Focus on reducing {highest_category} debt immediately.")
                elif highest_score > 40:
                    st.info(f"ℹ️ Recommendation: Address {highest_category} issues in upcoming sprints.")
                else:
                    st.success("✅ Good: Technical debt is at manageable levels.")
                
                # Category-specific advice
                st.markdown("### Category-Specific Advice")
                
                debt_advice = {
                    "Complexity": """
                    * Break down complex functions into smaller, focused methods
                    * Simplify conditional logic using guard clauses
                    * Consider refactoring to design patterns that reduce complexity
                    """,
                    "Duplication": """
                    * Extract duplicate code into shared utility functions
                    * Apply the DRY (Don't Repeat Yourself) principle
                    * Use inheritance or composition for shared behaviors
                    """,
                    "Documentation": """
                    * Add docstrings to all public functions and classes
                    * Document complex algorithms and business logic
                    * Ensure comments explain "why" not just "what"
                    """,
                    "Code Smells": """
                    * Address magic numbers and hardcoded values
                    * Fix naming inconsistencies
                    * Remove commented-out code and debugging statements
                    """,
                    "Test Coverage": """
                    * Add unit tests for critical business logic
                    * Ensure edge cases are covered
                    * Consider implementing test-driven development
                    """
                }
                
                # Display advice for the highest debt category
                normalized_category = highest_category.replace(" ", "").lower()
                for category, advice in debt_advice.items():
                    if category.lower() in normalized_category:
                        st.markdown(advice)
                        break
            else:
                st.info("No technical debt details available.")
        else:
            st.info("No technical debt data available.")
    
    # Tab 3: Metrics
    with tab3:
        st.header("Performance Metrics")
        
        results = st.session_state.analysis_results
        
        # Calculate current metrics
        total_issues = len(results["issues"])
        review_time_mins = results["review_time"] / 60
        issue_density = total_issues / max(1, sum(len(content) for content in results["code_contents"].values()) / 1000)
        
        # Display current metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Issues Found", 
                total_issues, 
                help="Total number of issues detected across all files"
            )
        
        with col2:
            st.metric(
                "Review Time", 
                f"{review_time_mins:.1f} mins", 
                help="Time taken to analyze all files"
            )
        
        with col3:
            st.metric(
                "Issue Density", 
                f"{issue_density:.1f} per KLOC", 
                help="Number of issues per 1000 lines of code"
            )
        
        # Load historical data for comparison
        historical_data = load_previous_analyses(st.session_state.current_repo)
        
        if historical_data:
            st.subheader("Historical Comparison")
            
            # Prepare data for visualization
            history_df = pd.DataFrame(historical_data)
            
            # Create charts for historical metrics
            col1, col2 = st.columns(2)
            
            with col1:
                issues_chart = alt.Chart(history_df).mark_line().encode(
                    x="date",
                    y="issue_count",
                    tooltip=["date", "issue_count", "pr_number"]
                ).properties(
                    title="Issues Found Over Time",
                    width=400,
                    height=300
                )
                
                st.altair_chart(issues_chart, use_container_width=True)
            
            with col2:
                time_chart = alt.Chart(history_df).mark_line().encode(
                    x="date",
                    y="review_time_mins",
                    tooltip=["date", "review_time_mins", "pr_number"]
                ).properties(
                    title="Review Time Over Time",
                    width=400,
                    height=300
                )
                
                st.altair_chart(time_chart, use_container_width=True)
            
            # Calculate averages
            avg_issues = history_df["issue_count"].mean()
            avg_time = history_df["review_time_mins"].mean()
            
            # Compare current with historical
            st.subheader("Comparison with Historical Average")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Issues vs. Average", 
                    f"{total_issues}",
                    delta=f"{total_issues - avg_issues:.1f}",
                    delta_color="inverse"  # Fewer issues is better
                )
            
            with col2:
                st.metric(
                    "Time vs. Average", 
                    f"{review_time_mins:.1f} mins",
                    delta=f"{review_time_mins - avg_time:.1f}",
                    delta_color="inverse"  # Less time is better
                )
        else:
            st.info("No historical data available for comparison.")
    
    # Tab 4: Feedback
    with tab4:
        st.header("Developer Feedback")
        
        if not st.session_state.feedback_submitted:
            st.subheader("Help us improve the AI-augmented review")
            
            with st.form("feedback_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    satisfaction = st.slider(
                        "Overall satisfaction with AI review",
                        1, 5, 3,
                        help="1=Not at all satisfied, 5=Extremely satisfied"
                    )
                    
                    accuracy = st.slider(
                        "Accuracy of identified issues",
                        1, 5, 3,
                        help="1=Mostly incorrect, 5=Highly accurate"
                    )
                    
                    relevance = st.slider(
                        "Relevance of the suggestions",
                        1, 5, 3,
                        help="1=Not relevant, 5=Highly relevant"
                    )
                
                with col2:
                    time_saved = st.slider(
                        "Estimated time saved (minutes)",
                        0, 120, 30,
                        help="Compared to manual review"
                    )
                    
                    human_review = st.radio(
                        "Would this replace human review?",
                        options=["No, it's complementary", "Yes, for some PRs", "Yes, for most PRs"],
                        index=0
                    )
                    
                    review_preference = st.radio(
                        "For your next code review, would you prefer:",
                        options=["AI only", "AI + human", "Human only"],
                        index=1
                    )
                
                additional_feedback = st.text_area(
                    "Additional comments or suggestions",
                    placeholder="Please share any other thoughts about the AI review..."
                )
                
                submitted = st.form_submit_button("Submit Feedback")
                
                if submitted:
                    # Save feedback
                    feedback_data = {
                        "repository": st.session_state.current_repo,
                        "pr_number": st.session_state.current_pr,
                        "satisfaction": satisfaction,
                        "accuracy": accuracy,
                        "relevance": relevance,
                        "time_saved": time_saved,
                        "human_review": human_review,
                        "review_preference": review_preference,
                        "additional_feedback": additional_feedback,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    save_feedback(feedback_data)
                    
                    st.session_state.feedback_submitted = True
                    st.success("Thank you for your feedback! It helps us improve the AI review system.")
        else:
            st.success("Thank you for your feedback!")
            
            st.markdown("""
            ### How your feedback helps us improve
            
            Your feedback is invaluable in helping us refine our AI-augmented code review system. We use it to:
            
            * Tune the technical debt scoring algorithm
            * Improve issue detection accuracy
            * Enhance the user experience and visualization
            * Determine which types of analysis are most valuable
            
            We appreciate your contribution to making this tool better for all developers!
            """)

# Footer
st.markdown("---")
st.markdown(
    "AI-Augmented Code Review Assistant | Research Prototype by Sameer Mankotia| © 2025"
)