<div align="right">
  English | <a href="./第十六章%20毕业设计.md">中文</a>
</div>

# Chapter 16: Graduation Project - Building Your Own Multi-Agent Application

Congratulations on reaching the final chapter of the Hello-Agents tutorial! In the previous 15 chapters, we built the HelloAgents framework from scratch and learned about core agent concepts, multiple paradigms, tool systems, memory mechanisms, communication protocols, reinforcement learning training, and performance evaluation. In Chapters 13-15, we also demonstrated how to integrate all learned knowledge through three complete practical projects (Intelligent Travel Assistant, Automated Deep Research Agent, and Cyber Town).

Now, it's time for you to become a true agent system builder! This chapter will guide you in **building your own multi-agent application** and sharing your achievements with the community through open-source collaboration.

## 16.1 The Significance of the Graduation Project

### 16.1.1 Why Do a Graduation Project

The best way to learn technology is not by reading tutorials, but by **hands-on practice**. Through the previous chapters, you have mastered the theoretical knowledge and technical tools for building agent systems. However, the real challenge lies in: **How to apply this knowledge to real problems? How to design a complete system? How to handle various edge cases and exceptions?**

The core value of the graduation project is to cultivate your comprehensive application ability, selectively integrating all the knowledge learned previously (agent paradigms, tool systems, memory mechanisms, communication protocols, etc.) into a complete project.

Through the learning and practice in this chapter, we hope you can independently design and implement a complete agent application, skillfully use various functions of the HelloAgents framework, master basic Git and GitHub operations, learn to write clear project documentation, participate in open-source community collaborative development, and ultimately obtain a technical work you can showcase.

### 16.1.2 Form of the Graduation Project

Your graduation project will be submitted to the Hello-Agents co-creation project repository (`Co-creation-projects` directory) in the form of an **open-source project**. Specific requirements are as follows:

1. **Project Naming**: Use the format `{your-GitHub-username}-{project-name}`, for example `jjyaoao-CodeReviewAgent`

2. **Project Content**:
   - A runnable Jupyter Notebook (`.ipynb` file) or Python script
   - Complete dependency list (`requirements.txt`)
   - Clear README documentation (`README.md`)
   - Optional: demo videos, screenshots, datasets, etc.

3. **Submission Method**: Submit via GitHub Pull Request (PR)

4. **Review Process**: Community members will review your code, provide improvement suggestions, and merge into the main repository after approval

## 16.2 Project Topic Selection Guide

### 16.2.1 Topic Selection Principles

A good graduation project should be practical, solving real problems rather than technology for technology's sake. We need to pursue completion within limited time and resources while clearly demonstrating your technical capabilities.

### 16.2.2 Recommended Topic Directions

Here are some recommended project directions - you can choose one or propose your own ideas:

**(1) Productivity Tools**

- **Intelligent Code Review Assistant**: Automatically analyze code quality, discover potential bugs, provide optimization suggestions
- **Intelligent Documentation Generator**: Automatically generate API documentation and user manuals based on code
- **Intelligent Meeting Assistant**: Record meeting content, generate meeting minutes, extract action items
- **Intelligent Email Assistant**: Automatically classify emails, generate reply drafts, remind of important matters

**(2) Learning Assistance**

- **Intelligent Learning Partner**: Recommend learning resources based on learning progress, generate practice questions, answer questions
- **Intelligent Paper Assistant**: Help find literature, summarize papers, generate citations
- **Intelligent Programming Tutor**: Provide programming exercises, code review, learning path planning
- **Intelligent Language Learning Assistant**: Provide conversation practice, grammar correction, vocabulary expansion

**(3) Creative Entertainment**

- **Intelligent Story Generator**: Generate novels, scripts, poetry based on user input
- **Intelligent Game NPC**: Create game characters with personality who can naturally converse with players
- **Intelligent Music Recommendation**: Recommend music based on mood and scene, generate playlists
- **Intelligent Recipe Assistant**: Recommend recipes based on ingredients and taste, generate shopping lists

**(4) Data Analysis**

- **Intelligent Data Analyst**: Automatically analyze data, generate visualization charts, write analysis reports
- **Intelligent Stock Analysis**: Analyze stock data and news sentiment, provide investment advice
- **Intelligent Public Opinion Monitoring**: Monitor social media and news websites, analyze public opinion trends
- **Intelligent Competitive Analysis**: Collect competitor information, comparative analysis, generate reports

**(5) Life Services**

- **Intelligent Health Assistant**: Record health data, provide health advice, create exercise plans
- **Intelligent Financial Assistant**: Record income and expenses, analyze spending habits, provide financial advice
- **Intelligent Shopping Assistant**: Compare prices, recommend products, generate shopping lists
- **Intelligent Home Control**: Control smart home devices through natural language

### 16.2.3 Topic Selection Example

Let's illustrate how to select a topic and design a project through a specific example.

**Project Name**: Intelligent Code Review Assistant (CodeReviewAgent)

**Problem Analysis**: Code review is an important part of software development, but manual review is time-consuming and prone to missing issues. Existing static analysis tools can only find syntax errors and cannot understand code logic, so an intelligent assistant that can understand code semantics and provide in-depth analysis is needed.

**Core Functions**: This project will implement code quality analysis (check code style, naming conventions, comment completeness), potential bug detection (discover logic errors, boundary condition issues, resource leaks), performance optimization suggestions (identify performance bottlenecks, propose optimization solutions), security vulnerability scanning (detect SQL injection, XSS and other security issues), and best practice recommendations (propose improvements based on language features and design patterns).

**Expected Outcomes**: The final deliverable will be a runnable Jupyter Notebook demonstrating the complete review process, supporting mainstream languages like Python and JavaScript, capable of generating structured Markdown format review reports, and providing specific code examples and improvement suggestions.

## 16.3 Development Environment Preparation

### 16.3.1 Installing Necessary Tools

Before starting development, please ensure your development environment has the following tools installed:

**(1) Python Environment**

```bash
# Install HelloAgents
pip install "hello-agents[all]"
```

**(2) Git and GitHub**

```bash
# Check Git version
git --version

# Configure Git user information
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Configure GitHub SSH key (recommended)
# 1. Generate SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. Add public key to GitHub
# Copy the content of ~/.ssh/id_ed25519.pub
# Add in GitHub Settings > SSH and GPG keys

# 3. Test connection
ssh -T git@github.com
```

**(3) Jupyter Notebook**

```bash
# Install Jupyter
pip install jupyter notebook

# Or use JupyterLab (recommended)
pip install jupyterlab

# Start Jupyter
jupyter lab
```

### 16.3.2 Fork the Project Repository

**Step 1: Fork the Repository**

1. Visit the Hello-Agents repository: https://github.com/datawhalechina/Hello-Agents
2. Click the "Fork" button in the upper right corner, as shown in the red box in Figure 16.1
3. Select your GitHub account and create the Fork

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/16-figures/16-1.png" alt="" width="85%"/>
  <p>Figure 16.1 Fork Repository Steps</p>
</div>

**Step 2: Clone to Local**

```bash
# As shown in Figure 16.2, clone your forked repository
git clone git@github.com:your-username/Hello-Agents.git

# Enter project directory
cd Hello-Agents

# Add upstream repository (for syncing updates)
git remote add upstream https://github.com/datawhalechina/Hello-Agents.git

# View remote repositories
git remote -v
```

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/16-figures/16-2.png" alt="" width="85%"/>
  <p>Figure 16.2 Clone Repository to Local</p>
</div>

**Step 3: Create Development Branch**

```bash
# Create and switch to new branch
git checkout -b feature/your-project-name

# For example:
git checkout -b feature/code-review-agent
```

### 16.3.3 Project Directory Structure

Create your project folder in the `Co-creation-projects` directory:

```bash
# Enter co-creation projects directory
cd Co-creation-projects

# Create project folder (format: GitHub-username-project-name)
mkdir your-username-project-name

# For example:
mkdir jjyaoao-CodeReviewAgent

# Enter project directory
cd jjyaoao-CodeReviewAgent
```

Recommended project structure:

```
jjyaoao-CodeReviewAgent/
├── README.md              # Project documentation
├── requirements.txt       # Python dependency list
├── main.ipynb            # Main Jupyter Notebook
├── data/                 # Data files (optional)
│   ├── sample_code.py
│   └── test_cases.json
├── outputs/              # Output results (optional)
│   ├── review_report.md
│   └── screenshots/
├── src/                  # Source code (optional, if code is extensive)
│   ├── agents/
│   ├── tools/
│   └── utils/
└── .env.example          # Environment variable template
```

## 16.4 Project Development Guide

### 16.4.1 Writing README Documentation

README is the face of your project. A good README should contain the following:

```markdown
# Project Name

> One-sentence description of your project

## 📝 Project Introduction

Detailed introduction to your project:
- What problem does it solve?
- What are its special features?
- What scenarios is it suitable for?

## ✨ Core Features

- [ ] Feature 1: Description
- [ ] Feature 2: Description
- [ ] Feature 3: Description

## 🛠️ Technology Stack

- HelloAgents framework
- Agent paradigms used (e.g., ReAct, Plan-and-Solve, etc.)
- Tools and APIs used
- Other dependency libraries

## 🚀 Quick Start

### Environment Requirements

- Python 3.10+
- Other requirements

### Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### Configure API Keys

\`\`\`bash
# Create .env file
cp .env.example .env

# Edit .env file and fill in your API keys
\`\`\`

### Run Project

\`\`\`bash
# Start Jupyter Notebook
jupyter lab

# Open main.ipynb and run
\`\`\`

## 📖 Usage Examples

Show how to use your project, preferably with code examples and results.

## 🎯 Project Highlights

- Highlight 1: Explanation
- Highlight 2: Explanation
- Highlight 3: Explanation

## 📊 Performance Evaluation

If you have evaluation results, display them here:
- Accuracy: XX%
- Response time: XX seconds
- Other metrics

## 🔮 Future Plans

- [ ] Feature 1 to be implemented
- [ ] Feature 2 to be implemented
- [ ] Parts to be optimized

## 🤝 Contribution Guidelines

Issues and Pull Requests are welcome!

## 📄 License

MIT License

## 👤 Author

- GitHub: [@your-username](https://github.com/your-username)
- Email: your.email@example.com (optional)

## 🙏 Acknowledgments

Thanks to the Datawhale community and Hello-Agents project!
```

### 16.4.2 Writing requirements.txt

List all Python dependencies required for the project:

```txt
# Core dependencies
hello-agents[all]>=0.2.7

# Visualization (if needed)
matplotlib>=3.7.0
plotly>=5.14.0

# Web framework (if needed)
fastapi>=0.109.0
uvicorn>=0.27.0
```

### 16.4.3 Developing Jupyter Notebook

**(1) Notebook Structure Recommendations**

A good Jupyter Notebook should contain the following parts:

```python
# ========================================
# Part 1: Project Introduction
# ========================================

"""
# Project Name

## Project Introduction
Brief introduction to project goals and features

## Author Information
- Name: XXX
- GitHub: @XXX
- Date: 2025-XX-XX
"""

# ========================================
# Part 2: Environment Configuration
# ========================================

# Install dependencies
!pip install -q hello-agents[all]

# Import necessary libraries
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import BaseTool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========================================
# Part 3: Tool Definition
# ========================================

class CustomTool(BaseTool):
    """Custom tool class"""

    name = "tool_name"
    description = "Tool description"

    def run(self, query: str) -> str:
        """Tool execution logic"""
        # Implement your tool logic
        return "Result"

# ========================================
# Part 4: Agent Construction
# ========================================

# Create LLM
llm = HelloAgentsLLM()

# Create agent
agent = SimpleAgent(
    name="Agent Name",
    llm=llm,
    system_prompt="System prompt"
)

# Add tools
agent.add_tool(CustomTool())

# ========================================
# Part 5: Feature Demonstration
# ========================================

# Example 1: Basic functionality
print("=== Example 1: Basic Functionality ===")
result = agent.run("User input")
print(result)

# Example 2: Complex scenario
print("\n=== Example 2: Complex Scenario ===")
result = agent.run("Complex user input")
print(result)

# ========================================
# Part 6: Performance Evaluation (Optional)
# ========================================

# Evaluation code
# ...

# ========================================
# Part 7: Summary and Outlook
# ========================================

"""
## Project Summary

### Implemented Features
- Feature 1
- Feature 2

### Challenges Encountered
- Challenge 1 and solution
- Challenge 2 and solution

### Future Improvement Directions
- Improvement 1
- Improvement 2
"""
```

### 16.4.4 Testing Your Project

Before submission, use this checklist to determine if your project meets submission requirements:

```markdown
- [ ] Code runs normally without errors
- [ ] README documentation is complete with clear instructions
- [ ] requirements.txt contains all dependencies
- [ ] Clear usage examples provided
- [ ] Code has appropriate comments
- [ ] Output results meet expectations
- [ ] Common exception cases handled
- [ ] Project structure is clear with standardized file naming
- [ ] Large files properly handled (see next section)
```

### 16.4.5 Large File Handling Guide

**⚠️ Important: Avoid Oversized Main Repository**

To keep the Hello-Agents main repository lightweight, please follow these large file handling guidelines:

**(1) File Size Limits**

- **Total project size**: Not exceeding 5MB
- **Prohibited from direct submission**: Video files, large datasets, model files

**(2) Large File Handling Solutions**

If your project contains large files (datasets, videos, models, etc.), please use the following solutions:

**Solution 1: Use External Links (Recommended)**

Upload large files to external platforms and provide download links in README:

```markdown
## Datasets

The datasets used in this project are large. Please download from the following links:

- Dataset 1: [Baidu Netdisk](link) Extraction code: xxxx
- Dataset 2: [Google Drive](link)
- Demo video: [Bilibili](link) / [YouTube](link)
```

Recommended external platforms:
- **Datasets**: Baidu Netdisk, Google Drive, Kaggle, HuggingFace Datasets
- **Videos**: Bilibili, YouTube, Tencent Video
- **Models**: HuggingFace Models, ModelScope
- **Images**: GitHub Issues, image hosting services

**Solution 2: Create Independent Repository**

If the project has many resources, consider creating an independent data repository:

```markdown
## Project Resources

Due to the large amount of data and demo resources, a separate resource repository has been created:

- Resource repository: https://github.com/your-username/project-name-resources
- Contains: Datasets, demo videos, model files, test data, etc.

### Usage

\`\`\`bash
# Clone resource repository
git clone https://github.com/your-username/project-name-resources.git

# Copy data to project directory
cp -r project-name-resources/data ./data
\`\`\`
```

**Solution 3: Use Sample Data**

Only provide small-scale sample data in the main repository:

```python
# Explain in README
## Data Description

- `data/sample.csv`: Sample data (100 records)
- Complete dataset (100,000 records) download from [here](link)
```

**(3) Best Practice Example**

```
your-username-project-name/
├── README.md              # Contains external resource links
├── requirements.txt
├── main.ipynb
├── .gitignore            # Ignore large files
├── data/
│   └── sample.csv        # Sample data only (<1MB)
└── outputs/
    └── demo_result.png   # Demo results only (<1MB)
```

README explanation:

```markdown
## Data and Resources

### Sample Data
Project includes small-scale sample data for quick testing (located in `data/sample.csv`)

### Complete Dataset
Complete dataset (500MB) download from the following link:
- Baidu Netdisk: [Link] Extraction code: xxxx
- Extract to `data/` directory after download

### Demo Video
- Bilibili: [Project Demo Video](link)
- YouTube: [Demo Video](link)
```

## 16.5 Submitting Pull Request

### 16.5.1 Submitting Code to GitHub

**Step 1: Check Modifications**

```bash
# View modified files
git status
```

**Step 2: Add Files**

```bash
# Add all modified files
git add .

# Or add specific files
git add Co-creation-projects/your-username-project-name/
```

**Step 3: Commit Changes**

Commit messages should follow this format:

```bash
# Format: type: brief description
git commit -m "feat: Add XXX graduation project"
```

**Commit Type Specifications:**

- `feat`: New feature or project (use this type for graduation projects)
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code format adjustment (doesn't affect functionality)
- `refactor`: Code refactoring
- `test`: Test-related
- `chore`: Other modifications (e.g., dependency updates)

**Step 4: Push to GitHub**

```bash
# Push to your forked repository
git push origin feature/your-project-name
```

### 16.5.2 Creating Pull Request

**Step 1: Visit GitHub**

1. Visit your forked repository: `https://github.com/your-username/Hello-Agents`
2. Click the "Pull requests" tab, as shown in Figure 16.3
3. Click the "New pull request" button

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/16-figures/16-3.png" alt="" width="85%"/>
  <p>Figure 16.3 Creating Pull Request</p>
</div>

**Step 2: Select Branches**

- Base repository: `datawhalechina/Hello-Agents`
- Base branch: `main`
- Head repository: `your-username/Hello-Agents`
- Compare branch: `feature/your-project-name`

**Step 3: Fill in PR Information**

**⚠️ Important: Unified PR Title Format**

For easy management and retrieval, all graduation project PR titles must follow this format:

```
[Graduation Project] Project Name - Brief Description
```

Examples:
- `[Graduation Project] CodeReviewAgent - Intelligent Code Review Assistant`
- `[Graduation Project] StudyBuddy - AI Learning Partner`
- `[Graduation Project] DataAnalyst - Intelligent Data Analyst`

**PR Description Template:**

```markdown
## Project Information

- **Project Name**: XXX
- **Author**: @your-username
- **Project Type**: Productivity Tool/Learning Assistance/Creative Entertainment/Data Analysis/Life Service

## Project Introduction

Brief description of your project (2-3 sentences)

## Core Features

- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3

## Technical Highlights

- Used XXX paradigm
- Implemented XXX functionality
- Optimized XXX performance

## Demo Effects

(Optional) Add screenshots or GIFs to showcase project effects

## Self-Check List

- [ ] Code runs normally
- [ ] README documentation complete
- [ ] requirements.txt complete
- [ ] Clear usage examples provided
- [ ] Code has appropriate comments

## Other Notes

(Optional) Other content that needs explanation
```

**Step 4: Submit PR**

As shown in Figure 16.4, click the "Create pull request" button to submit.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/16-figures/16-4.png" alt="" width="85%"/>
  <p>Figure 16.4 Submit Pull Request</p>
</div>

### 16.5.3 Responding to Review Comments

After submitting the PR, community members will review your code and provide suggestions. Please respond promptly:

1. **View Comments**: Check reviewer comments on the PR page
2. **Modify Code**: Modify code based on suggestions
3. **Submit Updates**:
   ```bash
   git add .
   git commit -m "fix: Modify XXX based on review comments"
   git push origin feature/your-project-name
   ```
4. **Reply to Comments**: Reply to reviewers on GitHub, explaining your modifications

## 16.6 Example Project Showcase

To help you better understand graduation project requirements, here's a complete example project. Don't worry - small creative ideas can also be included. Any work you create yourself is worth cherishing.

**Project Information**

- **Project Name**: CodeReviewAgent
- **Author**: @jjyaoao
- **Project Path**: `Co-creation-projects/jjyaoao-CodeReviewAgent/`

**Project Structure**

```
jjyaoao-CodeReviewAgent/
├── README.md              # Project documentation
├── requirements.txt       # Dependency list
├── main.ipynb            # Main program (includes quick demo and full features)
├── .env.example          # Environment variable example
├── .gitignore            # Git ignore rules
├── data/
│   └── sample_code.py    # Sample code
└── outputs/
    └── review_report.md  # Sample report
```

**Core Code Snippet (main.ipynb)**

```python
# ========================================
# Intelligent Code Review Assistant
# ========================================

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import Tool, ToolParameter
from typing import Dict, Any, List
import ast
import os

# ========================================
# 0. Configure LLM Parameters
# ========================================

os.environ["LLM_MODEL_ID"] = "Qwen/Qwen2.5-72B-Instruct"
os.environ["LLM_API_KEY"] = "your_api_key_here"
os.environ["LLM_BASE_URL"] = "https://api-inference.modelscope.cn/v1/"
os.environ["LLM_TIMEOUT"] = "60"

# ========================================
# 1. Define Code Analysis Tools
# ========================================

class CodeAnalysisTool(Tool):
    """Code static analysis tool"""

    def __init__(self):
        super().__init__(
            name="code_analysis",
            description="Analyze Python code structure, complexity, and potential issues"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """Analyze code and return results"""
        code = parameters.get("code", "")
        if not code:
            return "Error: Code cannot be empty"

        try:
            tree = ast.parse(code)
            functions = [node for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree)
                      if isinstance(node, ast.ClassDef)]

            result = {
                "Number of functions": len(functions),
                "Number of classes": len(classes),
                "Lines of code": len(code.split('\n')),
                "Function list": [f.name for f in functions],
                "Class list": [c.name for c in classes]
            }
            return str(result)
        except SyntaxError as e:
            return f"Syntax error: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="Python code to analyze",
                required=True
            )
        ]

class StyleCheckTool(Tool):
    """Code style checking tool"""

    def __init__(self):
        super().__init__(
            name="style_check",
            description="Check if code complies with PEP 8 standards"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """Check code style"""
        code = parameters.get("code", "")
        if not code:
            return "Error: Code cannot be empty"

        issues = []
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 79:
                issues.append(f"Line {i}: Exceeds 79 characters")
            if line.startswith(' ') and not line.startswith('    '):
                if len(line) - len(line.lstrip()) not in [0, 4, 8, 12]:
                    issues.append(f"Line {i}: Non-standard indentation")

        if not issues:
            return "Code style is good, complies with PEP 8 standards"
        return "Found the following issues:\n" + "\n".join(issues)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="Python code to check",
                required=True
            )
        ]

# ========================================
# 2. Create Tool Registry and Agent
# ========================================

# Create tool registry
tool_registry = ToolRegistry()
tool_registry.register_tool(CodeAnalysisTool())
tool_registry.register_tool(StyleCheckTool())

# Initialize LLM
llm = HelloAgentsLLM()

# Define system prompt
system_prompt = """You are an experienced code review expert. Your tasks are:

1. Use code_analysis tool to analyze code structure
2. Use style_check tool to check code style
3. Based on analysis results, provide detailed review report

The review report should include:
- Code structure analysis
- Style issues
- Potential bugs
- Performance optimization suggestions
- Best practice recommendations

Please output the report in Markdown format."""

# Create agent
agent = SimpleAgent(
    name="Code Review Assistant",
    llm=llm,
    system_prompt=system_prompt,
    tool_registry=tool_registry
)

# ========================================
# 3. Run Example
# ========================================

# Read sample code
with open("data/sample_code.py", "r", encoding="utf-8") as f:
    sample_code = f.read()

print("=== Code to Review ===")
print(sample_code)
print("\n" + "="*50 + "\n")

# Execute code review
print("=== Starting Code Review ===")
review_result = agent.run(f"Please review the following Python code:\n\n```python\n{sample_code}\n```")

print(review_result)

# Save review report
with open("outputs/review_report.md", "w", encoding="utf-8") as f:
    f.write(review_result)

print("\nReview report saved to outputs/review_report.md")
```

**README.md Example**

```markdown
# CodeReviewAgent - Intelligent Code Review Assistant

> Intelligent code review tool based on HelloAgents framework

## 📝 Project Introduction

CodeReviewAgent is an intelligent code review assistant that can automatically analyze Python code quality, discover potential issues, and provide optimization suggestions.

### Core Features

- ✅ Code structure analysis: Count functions, classes, lines of code, etc.
- ✅ Style checking: Check compliance with PEP 8 standards
- ✅ Intelligent suggestions: Provide in-depth analysis and optimization suggestions based on LLM
- ✅ Report generation: Generate review reports in Markdown format

## 🛠️ Technology Stack

- HelloAgents framework (SimpleAgent + ToolRegistry)
- Python AST module (code parsing)
- ModelScope API (Qwen2.5-72B model)

## 🚀 Quick Start

### Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### Configure LLM Parameters

**Method 1: Use .env file**

\`\`\`bash
cp .env.example .env
# Edit .env file and fill in your API key
\`\`\`

**Method 2: Set directly in Notebook**

The project is pre-configured with ModelScope API and can run directly. To modify, edit the configuration code in Part 1 of main.ipynb.

### Run Project

\`\`\`bash
jupyter lab
# Open main.ipynb and run all cells
\`\`\`

## 📖 Usage Example

1. Place code to review in `data/sample_code.py`
2. Run `main.ipynb`
3. View generated review report `outputs/review_report.md`

## 🎯 Project Highlights

- **Automation**: No need for manual line-by-line checking, automatically discovers issues
- **Intelligence**: Uses LLM to understand code semantics and provide in-depth suggestions
- **Extensibility**: Easy to add new checking rules and tools

## 👤 Author

- GitHub: [@jjyaoao](https://github.com/jjyaoao)
- Project link: [CodeReviewAgent](https://github.com/datawhalechina/Hello-Agents/tree/main/Co-creation-projects/jjyaoao-CodeReviewAgent)

## 🙏 Acknowledgments

Thanks to the Datawhale community and Hello-Agents project!
```

## 16.7 Summary and Outlook

By completing the graduation project, you should have mastered the complete process of agent system design: designing system architecture from requirements, skillfully using various functions and components of the HelloAgents framework, developing custom tools to extend agent capabilities, completing full project development from requirement analysis to code implementation, learning to use Git and GitHub for open-source collaboration, and writing clear technical documentation.

In this project, we built the HelloAgents framework from scratch and used it to implement multiple practical applications. Completing the graduation project is just the beginning. You can continue to deepen your learning of more agent paradigms and algorithms, prompt engineering and context engineering, multi-agent collaboration mechanisms, and other theoretical knowledge. You can also expand your technology stack by learning web development to build complete applications, learning databases to implement data persistence, and learning deployment to launch applications online. You can also continuously optimize your project by adding more features, optimizing performance and user experience, and improving testing and documentation. More importantly, actively participate in community contributions by helping other learners, participating in Hello-Agents framework development, and sharing your experiences and insights.

From the simple agent in Chapter 1 to now being able to independently build complete multi-agent applications, you have traveled through an exciting learning journey. But this is not the end - it's a new beginning.

AI technology is changing rapidly, and the agent field is full of infinite possibilities. We hope you can maintain curiosity and continuously learn new technologies, courageously use AI technology to solve practical problems and create value, willingly share your experiences and achievements with the community, and constantly refine your work in pursuit of excellence.

Finally, thank you for reading this project in its entirety. We hope you have gained something from the learning process and that you can apply what you've learned to actual projects, creating amazing agent applications. The future of AI is full of infinite possibilities - let's explore and create together!

**Remember: The best way to learn is through hands-on practice!**

Now, start building your own agent application! We look forward to seeing your excellent work in the Co-creation-projects directory!

If you find the Hello-Agents project helpful, please give us a ⭐Star!

---
<div align="center">
  <strong>🎓 Congratulations on completing the Hello-Agents tutorial! 🎉</strong>
</div>

