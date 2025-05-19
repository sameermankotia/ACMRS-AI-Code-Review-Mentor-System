# AI-Augmented Code Review Assistant: ACMRS

This tool enhances traditional code review processes by combining multiple analysis techniques with human oversight. It identifies potential issues, calculates technical debt, and provides actionable suggestions to improve code quality.

## Features

- **Multi-Level Analysis**: Combines static code analysis, LLM-powered semantic analysis, and human oversight
- **Technical Debt Scoring**: Calculates technical debt with detailed breakdown by category
- **Interactive Visualizations**: Displays annotated code, issue distribution, and technical debt metrics
- **Developer Feedback**: Collects reviewer feedback to continuously improve the system
- **Historical Metrics**: Tracks review performance over time to measure effectiveness

## Prerequisites

- Python 3.8 or higher
- GitHub personal access token with repo scope
- OpenAI API key (for LLM analysis)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/ai-code-review.git
   cd ai-code-review
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Create a .env file with your API keys:
   ```
   GITHUB_TOKEN=your_github_token
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Enter your GitHub token when prompted (or the app will use it from the .env file if available)

3. Enter the repository (in the format "owner/repo") and pull request number you want to analyze

4. Configure the analysis options and click "Run Analysis"

5. Review the results and provide feedback to help improve future analyses

## Components

- **app.py**: Main Streamlit application with user interface
- **github_utils.py**: GitHub API integration for PR and file handling
- **analysis_engine.py**: Core analysis logic for static and LLM-based review
- **visualizations.py**: Rendering functions for code and metrics visualization
- **data_handler.py**: Persistence layer for storing and retrieving analysis data

## Validation Approach

To validate the effectiveness of this tool:

1. **Human vs. AI Comparison**: Compare issues detected by human reviewers vs. the AI system
2. **Developer Satisfaction**: Measure developer satisfaction with the AI suggestions
3. **Time Savings**: Quantify review time reduction compared to manual-only reviews
4. **Technical Debt Impact**: Track technical debt over time in projects using the tool

## Paper Structure

This implementation serves as the foundation for an IEEE paper with the following structure:

1. **Introduction**: Problem statement and impact of technical debt
2. **Related Work**: Review of existing code review and technical debt tools
3. **Methodology**: Description of the AI-augmented code review approach
4. **Implementation**: Details of the prototype system (this repository)
5. **Evaluation**: Results from validation studies
6. **Discussion**: Implications for software development practices
7. **Conclusion**: Summary and future work

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.