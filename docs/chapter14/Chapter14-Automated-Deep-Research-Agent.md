<div align="right">
  English | <a href="./第十四章%20自动化深度研究智能体.md">中文</a>
</div>

# Chapter 14: Automated Deep Research Agent

In Chapter 13's travel assistant project, we experienced how to apply HelloAgents to a multi-agent product. In this chapter, we continue forward, focusing on **knowledge-intensive applications**: **building an agent assistant that can automatically execute deep research tasks.**

Compared to travel planning, the difficulty of deep research lies in the continuous divergence of information, rapid updates of facts, and users' high requirements for citation sources. To deliver trustworthy research reports, we need to equip agents with three core capabilities:

**(1) Problem Analysis**: Decompose users' open topics into retrievable query statements.

**(2) Multi-Round Information Collection**: Continuously mine materials by combining different search APIs and deduplicate and integrate them.

**(3) Reflection and Summarization**: Identify knowledge gaps based on stage results, decide whether to continue retrieval, and generate structured summaries.

## 14.1 Project Overview and Architecture Design

### 14.1.1 Why We Need a Deep Research Assistant

In the era of information explosion, we need to quickly understand new technologies, concepts, or events every day. Traditional research methods have several pain points. First is **information overload**. Search engines return thousands of results, and you need to click on links one by one and read a lot of content to find useful information. Second is **lack of structure**. Even if you find relevant information, this information is often fragmented and lacks systematic organization. Finally is **repetitive labor**. Every time you research a new topic, you need to repeat the process of "search → read → summarize → organize".

This is the problem that the deep research assistant needs to solve. It's not just a search tool, but a research assistant that can autonomously plan, execute, and summarize.

**Core Value of Deep Research Assistant:**

1. **Save Time**: Compress 1-2 hours of research work into 5-10 minutes
2. **Improve Quality**: Systematic research process to avoid missing important information
3. **Traceable**: Record all search results and sources for easy verification and citation
4. **Extensible**: Easily add new search engines, data sources, and analysis tools

### 14.1.2 Technical Architecture Overview

This system still adopts the classic **front-end and back-end separation architecture**, as shown in Figure 14.1.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-1.png" alt="" width="85%"/>
  <p>Figure 14.1 Deep Research Assistant Technical Architecture</p>
</div>

The system is designed with a four-layer architecture:

**Front-End Layer (Vue3+TypeScript)**: Full-screen modal dialog UI, Markdown result visualization

**Back-End Layer (FastAPI)**: API routing (`/research/stream`)

**Agent Layer (HelloAgents)**: Three specialized Agents (TODO Planner, Task Summarizer, Report Writer) + Two core tools (SearchTool, NoteTool)

**External Service Layer**: Search engines + LLM providers

Let's see how a complete research request flows through the system, as shown in Figure 14.2:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-2.png" alt="" width="85%"/>
  <p>Figure 14.2 Deep Research Assistant Data Flow Process</p>
</div>

1. **User Input**: User enters research topic on the front-end
2. **Front-End Sends**: Front-end connects to `/research/stream` via SSE
3. **Back-End Receives**: FastAPI receives request, creates research state
4. **Planning Phase**: Calls research planning Agent, decomposes into 3 subtasks
5. **Execution Phase**: Executes each subtask one by one
   - Use SearchTool to search
   - Call task summarization Agent to summarize
   - Use NoteTool to record results
6. **Report Phase**: Call report generation Agent, integrate all summaries
7. **Stream Return**: Push progress and results to front-end via SSE
8. **Front-End Display**: Front-end updates task status, progress bar, logs, and report in real-time

The project directory structure is as follows:

```
helloagents-deepresearch/
├── backend/                    # Back-end code
│   ├── src/
│   │   ├── agent.py           # Core coordinator
│   │   ├── main.py            # FastAPI entry
│   │   ├── models.py          # Data models
│   │   ├── prompts.py         # Prompt templates
│   │   ├── config.py          # Configuration management
│   │   └── services/          # Service layer
│   │       ├── planner.py     # Planning service
│   │       ├── summarizer.py  # Summarization service
│   │       ├── reporter.py    # Report service
│   │       └── search.py      # Search service
│   ├── .env                   # Environment variables
│   ├── pyproject.toml         # Dependency management
│   └── workspace/             # Research notes
│
└── frontend/                   # Front-end code
    ├── src/
    │   ├── App.vue            # Main component
    │   ├── components/        # UI components
    │   │   └── ResearchModal.vue
    │   └── composables/       # Composable functions
    │       └── useResearch.ts
    ├── package.json           # npm dependencies
    └── vite.config.ts         # Build configuration
```

### 14.1.3 Quick Experience: Run the Project in 5 Minutes

Before diving into implementation details, let's first run the project to see the final result. This way you'll have an intuitive understanding of the entire system.

You can check versions with the following commands:

```bash
python --version  # Should show Python 3.10.x or higher
node --version    # Should show v16.x.x or higher
npm --version     # Should show 8.x.x or higher
```

**(1) Start the Back-End**

```bash
# 1. Enter back-end directory
cd helloagents-deepresearch/backend

# 2. Install dependencies
# Method 1: Using uv (recommended, faster Python package manager)
uv sync

# Method 2: Using pip
pip install -e .

# 3. Configure environment variables
cp .env.example .env

# 4. Edit .env file, fill in your API keys
# Open .env file with your favorite editor
# At minimum, configure:
# - LLM_PROVIDER (e.g., openai, deepseek, qwen)
# - LLM_API_KEY (your LLM API key)
# - SEARCH_API (e.g., duckduckgo, tavily)

# 5. Start back-end
python src/main.py
```

If everything is normal, you'll see output similar to:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**(2) Start the Front-End**

Open a new terminal window:

```bash
# 1. Enter front-end directory
cd helloagents-deepresearch/frontend

# 2. Install dependencies
npm install

# 3. Start front-end
npm run dev
```

If everything is normal, you'll see output similar to:

```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:5174/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**(3) Start Research**

Open your browser and visit `http://localhost:5174`. You'll see a centered input card, as shown in Figure 14.3. Enter a research topic, for example `What kind of organization is Datawhale?`, select a search engine (if multiple are configured), and click the "Start Research" button.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-3.png" alt="" width="85%"/>
  <p>Figure 14.3 Deep Research Assistant Search Page</p>
</div>

As shown in Figure 14.4, the system will automatically expand to full screen, with research information displayed on the left and research progress and results displayed in real-time on the right. The entire research process takes about 1-3 minutes, depending on the complexity of the topic and the response speed of the search engine.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-4.png" alt="" width="85%"/>
  <p>Figure 14.4 Deep Research Assistant Expanded Research</p>
</div>

After research is complete, you'll see:

- **Task List**: Shows all subtasks and their status
- **Progress Log**: Shows all operations during the research process
- **Final Report**: Structured Markdown report containing summaries of all subtasks and source citations

Now you've successfully run the deep research assistant and have an intuitive understanding of the system.

## 14.2 TODO-Driven Research Paradigm

### 14.2.1 What is TODO-Driven Research

Traditional search engines can only answer single questions, while deep research needs to answer a series of related questions. The TODO-driven research paradigm decomposes complex research topics into multiple subtasks (TODOs), executes them one by one, and integrates the results.

The core idea of this paradigm is: **Transform the complex task of "research" into a "planning → execution → integration" process**.

Let's understand this transformation through an example. Suppose you want to research "What kind of organization is Datawhale?". The traditional search method is:

```
User input: What kind of organization is Datawhale?
Search engine: Returns 10-20 links
User: Click on links one by one, read content, take notes
Result: Fragmented information, lacking systematization
```

The problem with this approach is that each link only covers one aspect of the topic, lacks systematic structure, and requires manual organization and summarization.

**TODO-Driven Approach: Systematic Research**

```
User input: What kind of organization is Datawhale?

System planning:
  ├─ TODO 1: Basic information about Datawhale (organizational positioning)
  ├─ TODO 2: Main projects of Datawhale (core content)
  ├─ TODO 3: Community culture of Datawhale (values)
  └─ TODO 4: Influence of Datawhale (social contribution)

System execution:
  For each TODO:
    1. Search for relevant materials
    2. Summarize key information
    3. Record source citations

System integration:
  Generate structured report:
    ├─ Part 1: Organizational positioning (from TODO 1)
    ├─ Part 2: Core content (from TODO 2)
    ├─ Part 3: Values (from TODO 3)
    ├─ Part 4: Social contribution (from TODO 4)
    └─ References: All source citations
```

The advantages of this approach are that it decomposes complex topics into clear sub-questions, records search results and summaries for each subtask for easy traceability, and the systematic research process avoids missing important information. It's also easy to add new subtasks or adjust execution order.

A complete TODO-driven research system contains three core elements:

**(1) Intelligent Planner (TODO Planner)**: Responsible for decomposing research topics into subtasks. A good planner needs to understand the key aspects and research objectives of the topic, decompose the topic into 3-5 subtasks (too few won't cover everything, too many will be redundant), and design appropriate search queries for each subtask.

**(2) Task Executor**: Responsible for executing each subtask. The executor needs to use search engines to obtain relevant materials, extract key information and remove redundant content, while saving all source citations for easy verification.

**(3) Report Writer**: Responsible for integrating the results of all subtasks. The generator needs to organize content in logical order, merge duplicate information, and add source citations for each viewpoint.

In our case, the TODO-driven research process is shown in Figure 14.5:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-5.png" alt="" width="85%"/>
  <p>Figure 14.5 TODO-Driven Research Process</p>
</div>

The entire process is linear, but each stage has clear inputs and outputs. This design makes the system easy to understand and debug.

### 14.2.2 Three-Stage Research Process

The TODO-driven research process is divided into three stages: Planning, Execution, and Reporting. Each stage has a dedicated Agent responsible for it.

**(1) Stage 1: Planning**

The goal of the planning stage is to decompose the research topic into 3-5 subtasks. The system receives the research topic and current date as input, and outputs a JSON-format list of subtasks. Each subtask contains three fields: title (task title), intent (research intent), and query (search query).

The research planning Agent adopts different decomposition strategies based on topic characteristics, usually starting with basic concepts, then understanding technical status, practical applications, and development trends, and conducting comparative analysis when necessary. For example, for "What kind of organization is Datawhale?", the planning Agent might generate the following subtasks:

```json
[
  {
    "title": "Basic information about Datawhale",
    "intent": "Understand Datawhale's organizational positioning, founding time, development history",
    "query": "Datawhale organization introduction history 2024"
  },
  {
    "title": "Main projects of Datawhale",
    "intent": "Understand Datawhale's core open source projects and tutorials",
    "query": "Datawhale projects tutorials open source 2024"
  },
  ...
]
```

A good plan should be comprehensive, logically clear, have precise queries, and an appropriate number of items.

**(2) Stage 2: Execution**

The execution stage executes each subtask one by one, searching and summarizing relevant materials. The system receives the subtask list and search engine configuration as input, and outputs a summary (Markdown format) and source citation list for each subtask. The execution process is as follows:

For each subtask, the executor will:

1. **Search for materials**: Use the configured search engine to execute the search

   ```python
   search_results = search_tool.run({
       "input": task.query,
       "backend": "tavily",
       "mode": "structured",
       "max_results": 5
   })
   ```

2. **Get search results**: Extract title, URL, snippet

   ```json
   {
     "results": [
       {
         "title": "What is a Multimodal Model?",
         "url": "https://example.com/multimodal-model",
         "snippet": "A multimodal model is an AI model that can process multiple types of data..."
       },
       ...
     ]
   }
   ```

3. **Call summarization Agent**: Summarize search results

   ```python
   summary = summarizer_agent.run(
       task=task,
       search_results=search_results
   )
   ```

4. **Record summary and sources**: Save to NoteTool

   ```python
   note_tool.run({
       "action": "create",
       "title": task.title,
       "content": f"## {task.title}\n\n{summary}\n\n## Sources\n{sources}",
       "tags": ["research", "summary"]
   })
   ```

The task summarization Agent will extract core viewpoints from each search result, merge similar information, retain important numbers, dates, names and other key data, and add source citations for each viewpoint. For example, for the search results of "Basic information about Datawhale", the summarization Agent might generate:

```markdown
## Basic Information about Datawhale

Datawhale is an open source organization focused on data science and AI, founded in 2018[1]. The organization's core mission is "for the learner, grow together with learners", committed to building a pure learning community[2].

**Core Positioning:**

1. **Open Source Education Platform**: Provides high-quality AI and data science learning resources[1]
2. **Learner Community**: Gathers tens of thousands of AI learners and practitioners[3]
3. **Knowledge Sharing**: Advocates open source spirit, all content is completely free and open[2]

**Development History:**

- **2018**: Datawhale was founded, released first open source tutorial[1]
- **2020**: Became one of the leading AI learning communities in China[3]
- **2024**: Released 50+ open source projects, impacting 100,000+ learners[4]

## Sources

[1] https://github.com/datawhalechina
[2] https://datawhale.club/about
[3] https://www.zhihu.com/org/datawhale
[4] https://datawhale.cn
```

During execution, the system will push progress information to the front-end in real-time:

```json
{
  "type": "status",
  "message": "Searching: Basic information about Datawhale"
}
```

```json
{
  "type": "status",
  "message": "Summarizing search results..."
}
```

```json
{
  "type": "task",
  "task": {
    "id": 1,
    "title": "Basic information about Datawhale",
    "status": "completed"
  }
}
```

**(3) Stage 3: Reporting**

The goal of the reporting stage is to integrate the summaries of all subtasks and generate the final report. The system receives the summaries of all subtasks and the research topic as input, and outputs the final report in Markdown format. The report contains five parts: title, overview, detailed analysis of each subtask, summary, and references. For example, for "What kind of organization is Datawhale?", the final report might be:

```markdown
# What Kind of Organization is Datawhale?

## Overview

This report systematically researched the open source organization Datawhale, covering four aspects: basic information, main projects, community culture, and influence.

## 1. Basic Information about Datawhale

Datawhale is an open source organization focused on data science and AI, founded in 2018...

(Insert summary of subtask 1 here)

## 2. Main Projects of Datawhale

Datawhale has released multiple high-quality open source tutorials, including Hello-Agents, Joyful-Pandas, etc...

(Insert summary of subtask 2 here)
...
## Summary

Through this research, we learned about Datawhale's organizational positioning, core projects, community culture, and social contributions. Datawhale is a pure learning community that has made important contributions to AI education.

## References

[1] https://github.com/datawhalechina
[2] https://datawhale.club/about
...
```

The report generation Agent will organize content in the logical order of subtasks, add a brief overview at the beginning, merge duplicate information, unify Markdown format, and organize all source citations into the references section.

## 14.3 Agent System Design

### 14.3.1 Agent Responsibility Division

In the deep research assistant, we designed three specialized Agents, each responsible for a specific task. This makes each Agent simple, easy to understand and maintain.

In Chapter 7, we learned how to use `SimpleAgent` to build agents. The design philosophy of `SimpleAgent` is simple and direct: each time the `run()` method is called, the Agent analyzes the user's question, decides whether to call tools, and then returns the result. This design is very effective when handling simple tasks, but when facing complex tasks like deep research, we need to continue using a multi-agent collaboration approach.

As shown in Table 14.1, the three Agents are respectively responsible for planning, summarization, and report generation.

<div align="center">
  <p>Table 14.1 Responsibility Division of Three Agents</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-table-1.png" alt="" width="85%"/>
</div>

Let's introduce the design of each Agent in detail.

**Agent 1: Research Planning Expert (TODO Planner)**

**Responsibility**: Decompose research topics into 3-5 subtasks

**Design Philosophy**: The core task of the research planning expert is to understand the user's research topic, analyze the key aspects of the topic, and then generate a series of subtasks. This process is similar to the "brainstorming" stage of human researchers before starting research.

**Prompt Design**:

```python
todo_planner_instructions = """
You are a research planning expert. Your task is to decompose the user's research topic into 3-5 subtasks.

Current date: {current_date}

Research topic: {research_topic}

Please analyze this research topic and decompose it into 3-5 subtasks. Each subtask should:
1. Cover an important aspect of the topic
2. Have a clear research objective
3. Be able to find relevant materials through search engines

Please return the subtask list in JSON format, each subtask containing:
- title: Task title (concise and clear)
- intent: Task intent (why research this)
- query: Search query (query string for search engines, can use English for better search results)

Example output:
[
  {{
    "title": "What is a multimodal model",
    "intent": "Understand the basic concepts of multimodal models to lay the foundation for subsequent research",
    "query": "multimodal model definition concept 2024"
  }},
  ...
]

Please ensure:
1. Number of subtasks is between 3-5
2. Subtasks have logical relationships (e.g., from basics to applications, from current status to trends)
3. Search queries can accurately find relevant materials
4. Only return JSON, do not include other text
"""
```

**Key Design Points**: The prompt includes the current date to get the latest information, explicitly requires JSON format output for easy parsing, helps the Agent understand expected output through examples, and emphasizes constraints such as number of subtasks and logical relationships.

**Implementation Code**:

The ToolAwareSimpleAgent here is an extension of SimpleAgent. You can learn about it in Section 14.3.2, no need to delve into it here.

```python
class PlanningService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="TODO Planner",
            system_prompt="You are a research planning expert",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def plan_todo_list(self, state: SummaryState) -> List[TodoItem]:
        prompt = todo_planner_instructions.format(
            current_date=get_current_date(),
            research_topic=state.research_topic,
        )

        response = self._agent.run(prompt)
        tasks_payload = self._extract_tasks(response)

        todo_items = []
        for idx, item in enumerate(tasks_payload, start=1):
            task = TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            todo_items.append(task)

        return todo_items

    def _extract_tasks(self, response: str) -> List[dict]:
        """Extract JSON from Agent response"""
        # Use regex to extract JSON part
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("Unable to extract JSON from response")
```

**Agent 2: Task Summarization Expert (Task Summarizer)**

**Responsibility**: Summarize search results, extract key information

**Design Philosophy**: The core task of the task summarization expert is to read search results, extract key information, and present it in a structured way. This process is similar to human researchers taking notes after reading literature.

**Prompt Design**:

```python
task_summarizer_instructions = """
You are a task summarization expert. Your task is to summarize search results and extract key information.

Task title: {task_title}
Task intent: {task_intent}
Search query: {task_query}

Search results:
{search_results}

Please carefully read the above search results, extract key information, and return a summary in Markdown format.

The summary should include:
1. **Core Viewpoints**: Core viewpoints and conclusions from search results
2. **Key Data**: Important numbers, dates, names, etc.
3. **Source Citations**: Add source citations for each viewpoint (using [1], [2], etc.)

Please ensure:
1. Summary is concise and clear, avoiding redundancy
2. Retain important details and data
3. Add source citations for each viewpoint
4. Use Markdown format (headings, lists, bold, etc.)

Example output:
## Core Viewpoints

Multimodal models are AI models that can process multiple types of data[1]. Unlike traditional unimodal models, multimodal models can simultaneously understand text, images, audio, etc.[2].

**Key Features:**
- Cross-modal understanding[1]
- Unified representation[3]
- End-to-end training[2]

## Sources

[1] https://example.com/source1
[2] https://example.com/source2
[3] https://example.com/source3
"""
```

**Key Design Points**: The prompt includes task title, intent, query and other context to help the Agent understand the task, explicitly requires output to include core viewpoints, key data, and source citations, emphasizes adding source citations for each viewpoint, and helps the Agent understand the expected output format through examples.

**Implementation Code**:

```python
class SummarizationService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="Task Summarizer",
            system_prompt="You are a task summarization expert",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def summarize_task(
        self,
        task: TodoItem,
        search_results: List[dict]
    ) -> str:
        # Format search results
        formatted_sources = self._format_sources(search_results)

        prompt = task_summarizer_instructions.format(
            task_title=task.title,
            task_intent=task.intent,
            task_query=task.query,
            search_results=formatted_sources,
        )

        summary = self._agent.run(prompt)
        return summary

    def _format_sources(self, search_results: List[dict]) -> str:
        """Format search results"""
        formatted = []
        for idx, result in enumerate(search_results, start=1):
            formatted.append(
                f"[{idx}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Snippet: {result['snippet']}\n"
            )
        return "\n".join(formatted)
```

**Agent 3: Report Writing Expert (Report Writer)**

**Responsibility**: Integrate summaries of all subtasks and generate final report

**Design Philosophy**: The core task of the report writing expert is to integrate the summaries of all subtasks into a structured report. This process is similar to human researchers writing research reports after completing all investigations.

**Prompt Design**:

```python
report_writer_instructions = """
You are a report writing expert. Your task is to integrate the summaries of all subtasks and generate a structured research report.

Research topic: {research_topic}

Subtask summaries:
{task_summaries}

Please integrate all the above subtask summaries and generate a structured research report.

The report should include:
1. **Title**: Research topic
2. **Overview**: Briefly introduce the research topic and report structure (2-3 paragraphs)
3. **Detailed Analysis of Each Subtask**: Organize in logical order (using level-2 headings)
4. **Summary**: Summarize the main findings of the research (1-2 paragraphs)
5. **References**: All source citations (grouped by subtask)

Please ensure:
1. Report structure is clear and logically coherent
2. Eliminate duplicate information
3. Retain all source citations
4. Use Markdown format

Example output:
# Latest Advances in Multimodal Large Models

## Overview

This report systematically researched the latest advances in multimodal large models...

## 1. What is a Multimodal Model

(Insert summary of subtask 1 here)

## 2. What are the Latest Multimodal Models

(Insert summary of subtask 2 here)

...

## Summary

Through this research, we learned about...

## References

### Task 1: What is a Multimodal Model
[1] https://example.com/source1
...
"""
```

**Key Design Points**: The prompt explicitly requires the report to include title, overview, detailed analysis, summary, references and other structures, emphasizes organizing content in logical order, requires merging duplicate information to eliminate redundancy, and retains all source citations.

**Implementation Code**:

```python
class ReportingService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="Report Writer",
            system_prompt="You are a report writing expert",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def generate_report(
        self,
        research_topic: str,
        task_summaries: List[Tuple[TodoItem, str]]
    ) -> str:
        # Format subtask summaries
        formatted_summaries = self._format_summaries(task_summaries)

        prompt = report_writer_instructions.format(
            research_topic=research_topic,
            task_summaries=formatted_summaries,
        )

        report = self._agent.run(prompt)
        return report

    def _format_summaries(
        self,
        task_summaries: List[Tuple[TodoItem, str]]
    ) -> str:
        """Format subtask summaries"""
        formatted = []
        for idx, (task, summary) in enumerate(task_summaries, start=1):
            formatted.append(
                f"## Task {idx}: {task.title}\n"
                f"Intent: {task.intent}\n\n"
                f"{summary}\n"
            )
        return "\n".join(formatted)
```

### 14.3.2 ToolAwareSimpleAgent Design

In Chapter 7, we implemented `SimpleAgent`, which is the basic Agent of the HelloAgents framework. But in the deep research assistant, we need an Agent that can **record tool calls**. This is where `ToolAwareSimpleAgent` comes from.

In the deep research assistant, we need to record the tool call status of each Agent for:

1. **Debugging**: View which tools the Agent called and what parameters were passed
2. **Logging**: Record all operations during the research process
3. **Analysis**: Analyze the Agent's behavior patterns
4. **Progress Display**: Show in real-time what the Agent is doing

`SimpleAgent` itself does not support tool call listening, so we need to extend it.

`ToolAwareSimpleAgent` adds a `tool_call_listener` parameter on top of `SimpleAgent`. This is a callback function that is called every time a tool is called.

**Usage Example:**

```python
from hello_agents import ToolAwareSimpleAgent

def tool_listener(call_info):
    print(f"Agent: {call_info['agent_name']}")
    print(f"Tool: {call_info['tool_name']}")
    print(f"Parameters: {call_info['parsed_parameters']}")
    print(f"Result: {call_info['result']}")

agent = ToolAwareSimpleAgent(
    name="Research Assistant",
    system_prompt="You are a research assistant",
    llm=llm,
    tool_call_listener=tool_listener
)
```

`ToolAwareSimpleAgent` inherits from `SimpleAgent` and overrides the `_execute_tool_call` method:

```python
class ToolAwareSimpleAgent(SimpleAgent):
    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        tool_call_listener: Optional[Callable] = None,
    ):
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            llm=llm,
            tool_registry=tool_registry,
        )
        self._tool_call_listener = tool_call_listener

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """Execute tool call and notify listener"""
        # Parse parameters
        parsed_parameters = self._parse_parameters(parameters)

        # Call tool
        result = super()._execute_tool_call(tool_name, parameters)

        # Notify listener
        if self._tool_call_listener:
            self._tool_call_listener({
                "agent_name": self.name,
                "tool_name": tool_name,
                "parsed_parameters": parsed_parameters,
                "result": result,
            })

        return result
```

In the deep research assistant, we use `ToolAwareSimpleAgent` to record all Agent tool calls:

```python
class DeepResearchAgent:
    def __init__(self, config: Configuration):
        self.config = config
        self.llm = HelloAgentsLLM(...)

        # Create tool call listener
        def tool_listener(call_info):
            self._emit_event({
                "type": "tool_call",
                "agent": call_info["agent_name"],
                "tool": call_info["tool_name"],
                "parameters": call_info["parsed_parameters"],
            })

        # Create three Agents, all using the same listener
        self.planner = PlanningService(self.llm, tool_listener)
        self.summarizer = SummarizationService(self.llm, tool_listener)
        self.reporter = ReportingService(self.llm, tool_listener)
```

This way, all Agent tool calls are recorded and pushed to the front-end via SSE, displayed to the user in real-time.

### 14.3.3 Agent Collaboration Mode

The three Agents have a **sequential collaboration** relationship, as shown in Figure 14.6.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-6.png" alt="" width="85%"/>
  <p>Figure 14.6 Agent Collaboration Process</p>
</div>

The characteristics of the sequential collaboration mode are:

1. **Linear Process**: Agents execute in a fixed order
2. **Clear Input and Output**: Each Agent's input comes from the previous Agent's output
3. **No Concurrency**: Only one Agent is working at the same time

`DeepResearchAgent` is the core coordinator of the entire system, responsible for scheduling the three Agents:

```python
class DeepResearchAgent:
    def run(self, research_topic: str) -> str:
        # 1. Planning stage
        self._emit_event({"type": "status", "message": "Planning research tasks..."})
        todo_list = self.planner.plan_todo_list(research_topic)
        self._emit_event({"type": "tasks", "tasks": todo_list})

        # 2. Execution stage
        task_summaries = []
        for task in todo_list:
            self._emit_event({
                "type": "status",
                "message": f"Researching: {task.title}"
            })

            # Search
            search_results = self.search_service.search(task.query)

            # Summarize
            summary = self.summarizer.summarize_task(task, search_results)
            task_summaries.append((task, summary))

            self._emit_event({
                "type": "task_completed",
                "task_id": task.id
            })

        # 3. Reporting stage
        self._emit_event({"type": "status", "message": "Generating report..."})
        report = self.reporter.generate_report(research_topic, task_summaries)
        self._emit_event({"type": "report", "content": report})

        return report
```

## 14.4 Tool System Integration

### 14.4.1 SearchTool Extension

In Chapter 7, we implemented the basic version of `SearchTool`, integrating Tavily and SerpApi search engines, demonstrating the design idea of multi-source search. In this chapter's deep research assistant, we further extended the capabilities of `SearchTool`, adding DuckDuckGo, Perplexity, SearXNG and other search engines, and implementing Advanced mode (combining multiple search engines). Search is the most core function of the deep research assistant, and these extensions enable the system to adapt to different usage scenarios and needs.

As shown in Table 14.2, the search engines added this time have different characteristics and applicable scenarios.

<div align="center">
  <p>Table 14.2 Multi-Search Engine Comparison</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-table-2.png" alt="" width="85%"/>
</div>

We will no longer discuss how to extend separately. You can refer to the source code and the extension cases in Chapter 7 for implementation. `SearchTool` provides a unified search interface. No matter which search engine is used, the calling method is the same.

In the deep research assistant, we select the search engine through the configuration file:

```python
# config.py
class SearchAPI(str, Enum):
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    PERPLEXITY = "perplexity"
    SEARXNG = "searxng"
    ADVANCED = "advanced"

class Configuration(BaseModel):
    search_api: SearchAPI = SearchAPI.DUCKDUCKGO
    # ...
```

```python
# .env
SEARCH_API=tavily
```

This way, users can select the search engine by modifying the `.env` file without modifying the code.

The result returned by `SearchTool` is a dictionary containing:

- `results`: List of search results, each result contains title, URL, snippet
- `backend`: Search engine used
- `answer`: AI-generated answer (Perplexity only)
- `notices`: Notification information (such as API limits, errors, etc.)

Here are some special case handling.

Search results may contain duplicate URLs, we need to deduplicate:

```python
def deduplicate_sources(sources: List[dict]) -> List[dict]:
    """Remove duplicate URLs"""
    seen_urls = set()
    unique_sources = []

    for source in sources:
        if source["url"] not in seen_urls:
            seen_urls.add(source["url"])
            unique_sources.append(source)

    return unique_sources
```

Search results may contain a large amount of text, we need to limit the number of tokens for each source:

```python
def limit_source_tokens(source: dict, max_tokens: int = 2000) -> dict:
    """Limit the number of tokens for a source"""
    snippet = source["snippet"]

    # Simple token estimation: 1 token is approximately 4 characters
    max_chars = max_tokens * 4

    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + "..."

    return {
        **source,
        "snippet": snippet
    }
```

### 14.4.2 NoteTool Usage

In the deep research assistant, we use `NoteTool` to persist research progress. `NoteTool` is a built-in tool integrated in Chapter 9, used to create, read, update, and delete notes.

During the research process, we need to record the search results, summaries, and final research report for each subtask. This information needs to be persisted to disk so that research can continue from the last progress when interrupted, and it is also convenient to view all operations during the research process and analyze the quality and efficiency of the research.

`NoteTool` stores notes in the specified workspace directory, with each note being a Markdown file. The note filename is the task ID, and the content includes task title, task intent, search query, search results, and summary.

The final generated file style will be in the following tree structure:

```
workspace/
├── notes/
│   ├── 1.md  # Notes for task 1
│   ├── 2.md  # Notes for task 2
│   ├── 3.md  # Notes for task 3
│   └── ...
└── reports/
    └── final_report.md  # Final report
```

In the deep research assistant, we use `NoteTool` to record the research progress of each subtask:

```python
class NotesService:
    def __init__(self, workspace: str):
        self.note_tool = NoteTool(workspace=workspace)

    def save_task_summary(
        self,
        task: TodoItem,
        search_results: List[dict],
        summary: str
    ):
        """Save task summary"""
        # Format note content
        content = self._format_note_content(
            task=task,
            search_results=search_results,
            summary=summary
        )

        # Create note
        self.note_tool.run({
            "action": "create",
            "title": f"Task {task.id}: {task.title}",
            "content": content,
            "tags": ["research", "summary"]
        })

    def _format_note_content(
        self,
        task: TodoItem,
        search_results: List[dict],
        summary: str
    ) -> str:
        """Format note content"""
        content = f"# Task {task.id}: {task.title}\n\n"
        content += f"## Task Information\n\n"
        content += f"- **Intent**: {task.intent}\n"
        content += f"- **Query**: {task.query}\n\n"

        content += f"## Search Results\n\n"
        for idx, result in enumerate(search_results, start=1):
            content += f"[{idx}] {result['title']}\n"
            content += f"URL: {result['url']}\n"
            content += f"Snippet: {result['snippet']}\n\n"

        content += f"## Summary\n\n{summary}\n"

        return content
```

### 14.4.3 ToolRegistry Tool Management

`ToolRegistry` is the tool registry of the HelloAgents framework, also supported in our Chapter 7, used to manage the registration and invocation of all tools. In the deep research assistant, we use `ToolRegistry` to manage `SearchTool` and `NoteTool`.

Before creating an Agent, we need to register tools first:

```python
from hello_agents import ToolAwareSimpleAgent
from hello_agents.tools import ToolRegistry
from hello_agents.tools import SearchTool
from hello_agents.tools import NoteTool

# Create tools
search_tool = SearchTool(backend="hybrid")
note_tool = NoteTool(workspace="./workspace/notes")

# Create registry
registry = ToolRegistry()

# Register tools
registry.register_tool(search_tool)
registry.register_tool(note_tool)

# Create Agent
agent = ToolAwareSimpleAgent(
    name="Research Assistant",
    system_prompt="You are a research assistant",
    llm=llm,
    tool_registry=registry
)
```

When an Agent needs to call a tool, it generates a tool call instruction, as shown in Figure 14.7.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-7.png" alt="" width="85%"/>
  <p>Figure 14.7 Tool Call Process</p>
</div>

**Tool Call Process**:

1. **Agent generates instruction**: Agent generates tool call instruction, such as `[TOOL_CALL:search_tool:{"input": "Datawhale organization", "backend": "tavily"}]`
2. **Parse instruction**: `ToolRegistry` parses the instruction, extracts tool name and parameters
3. **Find tool**: `ToolRegistry` finds the corresponding tool based on the tool name
4. **Call tool**: Call the tool's `run` method, passing in parameters
5. **Return result**: Tool returns execution result
6. **Format result**: Format the result as a string and return it to the Agent

## 14.5 Service Layer Implementation

This section will introduce the implementation of core services in detail, including PlanningService, SummarizationService, ReportingService, and SearchService. These services are the bridge connecting Agents and tools, responsible for specific business logic.

### 14.5.1 Task Planning Service

`PlanningService` is responsible for calling the research planning Agent to decompose the research topic into subtasks. This is the first and most critical step of the entire research process.

**(1) Implementation Approach**

Its core responsibilities are:

1. **Build planning Prompt**: Build Prompt based on research topic and current date
2. **Call planning Agent**: Call TODO Planner Agent to generate subtask list
3. **Parse JSON response**: Extract JSON-format subtask list from Agent's response
4. **Validate subtask format**: Ensure each subtask contains required fields (title, intent, query)

```python
import re
import json
from typing import List, Callable, Optional
from datetime import datetime

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem, SummaryState
from prompts import todo_planner_instructions

class PlanningService:
    """Task planning service"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Create planning Agent
        self._agent = ToolAwareSimpleAgent(
            name="TODO Planner",
            system_prompt="You are a research planning expert, skilled at decomposing complex research topics into clear subtasks.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def plan_todo_list(self, state: SummaryState) -> List[TodoItem]:
        """Plan TODO list

        Args:
            state: Research state, containing research topic

        Returns:
            Subtask list
        """
        # Build Prompt
        prompt = todo_planner_instructions.format(
            current_date=self._get_current_date(),
            research_topic=state.research_topic,
        )

        # Call Agent
        response = self._agent.run(prompt)

        # Parse JSON
        tasks_payload = self._extract_tasks(response)

        # Validate and create TodoItem
        todo_items = []
        for idx, item in enumerate(tasks_payload, start=1):
            # Validate required fields
            if not all(key in item for key in ["title", "intent", "query"]):
                raise ValueError(f"Task {idx} is missing required fields")

            task = TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            todo_items.append(task)

        return todo_items

    def _get_current_date(self) -> str:
        """Get current date"""
        return datetime.now().strftime("%Y-%m-%d")

    def _extract_tasks(self, response: str) -> List[dict]:
        """Extract JSON from Agent response

        The Agent's response may contain extra text, such as:
        "Okay, I will plan the following tasks for you:\n[{...}, {...}]\nThese tasks cover..."

        We need to extract the JSON part.
        """
        # Method 1: Use regex to extract JSON array
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON parsing failed: {e}")

        # Method 2: If no JSON array is found, try to parse the entire response directly
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Unable to extract JSON from response")
```

**(2) JSON Parsing and Validation**

The JSON returned by the Agent may contain extra text or format errors, so we need robust parsing logic:

**Common Issues**:

1. **Contains extra text**: Agent may add explanatory text before and after JSON
2. **Format errors**: JSON may be missing quotes, commas, etc.
3. **Missing fields**: Some subtasks may be missing required fields

**Solutions**:

1. **Use regex**: Extract JSON part
2. **Multiple parsing strategies**: First try to extract JSON array, then try to parse directly
3. **Field validation**: Ensure each subtask contains required fields

**Example**:

```python
# Agent response example 1: Contains extra text
response1 = """
Okay, I will plan the following tasks for you:

[
  {
    "title": "What is a multimodal model",
    "intent": "Understand basic concepts",
    "query": "multimodal model definition"
  },
  {
    "title": "Latest multimodal models",
    "intent": "Understand technical status",
    "query": "latest multimodal models 2024"
  }
]

These tasks cover the basic information and core projects of the Datawhale organization.
"""

# Extract JSON
tasks1 = service._extract_tasks(response1)
# Result: [{"title": "Basic information about Datawhale", ...}, ...]

# Agent response example 2: Pure JSON
response2 = """
[
  {"title": "Basic information about Datawhale", "intent": "Understand organizational positioning", "query": "Datawhale organization introduction"},
  {"title": "Main projects of Datawhale", "intent": "Understand core content", "query": "Datawhale projects tutorials 2024"}
]
"""

# Extract JSON
tasks2 = service._extract_tasks(response2)
# Result: [{"title": "What is a multimodal model", ...}, ...]
```

**(3) Planning Quality Assessment**

A good plan should meet the following criteria:

1. **Comprehensive coverage**: Cover all important aspects of the topic
2. **Clear logic**: Clear logical relationships between subtasks
3. **Precise queries**: Search queries can accurately find relevant materials
4. **Appropriate quantity**: 3-5 subtasks

We can add an evaluation method:

```python
def evaluate_plan(self, todo_items: List[TodoItem]) -> dict:
    """Evaluate planning quality

    Returns:
        Evaluation results, including score and suggestions
    """
    score = 100
    suggestions = []

    # Check quantity
    if len(todo_items) < 3:
        score -= 20
        suggestions.append("Too few subtasks, may miss important information")
    elif len(todo_items) > 5:
        score -= 10
        suggestions.append("Too many subtasks, may have redundancy")

    # Check query quality
    for task in todo_items:
        if len(task.query.split()) < 2:
            score -= 10
            suggestions.append(f"Query for task '{task.title}' is too simple")

    # Check logical relationships
    # (More complex logic checks can be added here)

    return {
        "score": score,
        "suggestions": suggestions
    }
```

### 14.5.2 Summarization Service

`SummarizationService` is responsible for calling the task summarization Agent to summarize search results. This is the core link of the research process and determines the quality of the research.

Its responsibilities are:

1. **Format search results**: Format search results into readable text
2. **Build summarization Prompt**: Build Prompt based on task information and search results
3. **Call summarization Agent**: Call Task Summarizer Agent to generate summary
4. **Extract source citations**: Extract source citations from summary

Core code:

```python
from typing import List, Callable, Optional, Tuple

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem
from prompts import task_summarizer_instructions

class SummarizationService:
    """Summarization service"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Create summarization Agent
        self._agent = ToolAwareSimpleAgent(
            name="Task Summarizer",
            system_prompt="You are a task summarization expert, skilled at extracting key information from search results.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def summarize_task(
        self,
        task: TodoItem,
        search_results: List[dict]
    ) -> Tuple[str, List[str]]:
        """Summarize task

        Args:
            task: Task information
            search_results: Search results list

        Returns:
            (Summary text, source URL list)
        """
        # Format search results
        formatted_sources = self._format_sources(search_results)

        # Build Prompt
        prompt = task_summarizer_instructions.format(
            task_title=task.title,
            task_intent=task.intent,
            task_query=task.query,
            search_results=formatted_sources,
        )

        # Call Agent
        summary = self._agent.run(prompt)

        # Extract source URLs
        source_urls = [result["url"] for result in search_results]

        return summary, source_urls

    def _format_sources(self, search_results: List[dict]) -> str:
        """Format search results

        Format search results into readable text, including:
        - Serial number
        - Title
        - URL
        - Snippet
        """
        formatted = []
        for idx, result in enumerate(search_results, start=1):
            formatted.append(
                f"[{idx}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Snippet: {result['snippet']}\n"
            )
        return "\n".join(formatted)
```

### Report Structure Design

The final report should include the following parts:

## References

### Task 1: What is a Multimodal Model
- https://example.com/multimodal-model-definition
...

### Task 2: What are the Latest Multimodal Models
- https://example.com/gpt4v
...
...

### 14.5.3 Report Generation Service

`ReportingService` is responsible for calling the report generation Agent to integrate the summaries of all subtasks. This is the last step of the research process, generating the final research report.

Its responsibilities are:

1. **Format subtask summaries**: Format all subtask summaries into a unified format
2. **Build report Prompt**: Build Prompt based on research topic and subtask summaries
3. **Call report Agent**: Call Report Writer Agent to generate final report
4. **Organize citations**: Organize all source citations into the references section

**Core Code Implementation**:

```python
from typing import List, Callable, Optional, Tuple

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem
from prompts import report_writer_instructions

class ReportingService:
    """Report generation service"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Create report Agent
        self._agent = ToolAwareSimpleAgent(
            name="Report Writer",
            system_prompt="You are a report writing expert, skilled at integrating information and generating structured reports.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def generate_report(
        self,
        research_topic: str,
        task_summaries: List[Tuple[TodoItem, str, List[str]]]
    ) -> str:
        """Generate final report

        Args:
            research_topic: Research topic
            task_summaries: Subtask summary list, each element is (task, summary, source URL list)

        Returns:
            Final report (Markdown format)
        """
        # Format subtask summaries
        formatted_summaries = self._format_summaries(task_summaries)

        # Build Prompt
        prompt = report_writer_instructions.format(
            research_topic=research_topic,
            task_summaries=formatted_summaries,
        )

        # Call Agent
        report = self._agent.run(prompt)

        return report

    def _format_summaries(
        self,
        task_summaries: List[Tuple[TodoItem, str, List[str]]]
    ) -> str:
        """Format subtask summaries

        Format all subtask summaries into a unified format, including:
        - Task serial number
        - Task title
        - Task intent
        - Summary content
        - Source URLs
        """
        formatted = []
        for idx, (task, summary, source_urls) in enumerate(task_summaries, start=1):
            formatted.append(
                f"## Task {idx}: {task.title}\n\n"
                f"**Intent**: {task.intent}\n\n"
                f"{summary}\n\n"
                f"**Sources**:\n"
            )
            for url in source_urls:
                formatted.append(f"- {url}\n")
            formatted.append("\n")

        return "".join(formatted)
```

### 14.5.4 Search Scheduling Service

`SearchService` is responsible for scheduling search engines, executing searches, and returning results. This is the bridge connecting Agents and SearchTool. Here we did not adopt the usual form of having SimpleAgent directly call tools, but instead return the execution results of SearchTool to the Agent through an intermediate layer, which makes the Agent more focused on processing the obtained information.

Its responsibilities are:

1. **Schedule search engine**: Select search engine based on configuration
2. **Execute search**: Call SearchTool to execute search
3. **Process results**: Deduplicate, limit tokens, format
4. **Error handling**: Handle search failure situations

Core code:

```python
from typing import List, Optional
import logging

from hello_agents.tools import SearchTool
from config import Configuration

logger = logging.getLogger(__name__)

class SearchService:
    """Search scheduling service"""

    def __init__(self, config: Configuration):
        self.config = config

        # Create SearchTool
        self.search_tool = SearchTool(backend="hybrid")

    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[dict]:
        """Execute search

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            Search results list
        """
        try:
            # Call SearchTool
            raw_response = self.search_tool.run({
                "input": query,
                "backend": self.config.search_api.value,
                "mode": "structured",
                "max_results": max_results
            })

            # Extract results
            results = raw_response.get("results", [])

            # Process results
            results = self._deduplicate_sources(results)
            results = self._limit_source_tokens(results)

            logger.info(f"Search successful: {query}, returned {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"Search failed: {query}, error: {e}")
            return []

    def _deduplicate_sources(self, sources: List[dict]) -> List[dict]:
        """Remove duplicate URLs"""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(source)

        return unique_sources

    def _limit_source_tokens(
        self,
        sources: List[dict],
        max_tokens_per_source: int = 2000
    ) -> List[dict]:
        """Limit the number of tokens per source"""
        limited_sources = []

        for source in sources:
            snippet = source.get("snippet", "")

            # Simple token estimation: 1 token is approximately 4 characters
            max_chars = max_tokens_per_source * 4

            if len(snippet) > max_chars:
                snippet = snippet[:max_chars] + "..."

            limited_sources.append({
                **source,
                "snippet": snippet
            })

        return limited_sources
```

Select search engine based on configuration, as shown in Figure 14.8:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-8.png" alt="" width="85%"/>
  <p>Figure 14.8 Search Engine Scheduling Process</p>
</div>

**Scheduling Logic**:

1. **Read configuration**: Read `SEARCH_API` configuration from `.env` file
2. **Select engine**: Select search engine based on configuration (tavily, duckduckgo, perplexity, etc.)
3. **Execute search**: Call SearchTool to execute search
4. **Process results**: Deduplicate, limit tokens, format
5. **Return results**: Return processed search results

To improve efficiency and reduce costs, we can add search result caching:

```python
import hashlib
import json
from pathlib import Path

class SearchService:
    def __init__(self, config: Configuration):
        self.config = config
        self.search_tool = SearchTool(backend="hybrid")

        # Cache directory
        self.cache_dir = Path("./cache/search")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        query: str,
        max_results: int = 5,
        use_cache: bool = True
    ) -> List[dict]:
        """Execute search (with cache)"""
        # Generate cache key
        cache_key = self._generate_cache_key(query, max_results)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Try to read from cache
        if use_cache and cache_file.exists():
            logger.info(f"Reading search results from cache: {query}")
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Execute search
        results = self._execute_search(query, max_results)

        # Save to cache
        if use_cache and results:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    def _generate_cache_key(self, query: str, max_results: int) -> str:
        """Generate cache key"""
        # Generate MD5 hash using query and max results
        content = f"{query}_{max_results}_{self.config.search_api.value}"
        return hashlib.md5(content.encode()).hexdigest()
```

Through four core services (PlanningService, SummarizationService, ReportingService, SearchService), we built a complete research process. These services each perform their duties and collaborate through clear interfaces, achieving an automated process from research topic to final report.

## 14.6 Front-End Interaction Design

In the previous sections, we implemented the complete back-end system. This section will introduce the front-end interaction design in detail, including full-screen modal dialog UI, real-time progress display, and research result visualization.

### 14.6.1 Full-Screen Modal Dialog UI Design

The deep research assistant adopts a full-screen modal dialog UI design, which has the following advantages:

1. **Immersive experience**: Full-screen display, avoiding distractions, focusing on research
2. **Clear hierarchy**: Main page and research page are separated, with clear hierarchy
3. **Easy to close**: Click the close button or press ESC key to return to the main page
4. **Responsive design**: Adapts to different screen sizes

As shown in Figure 14.9, the full-screen modal dialog contains the following parts:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-9.png" alt="" width="85%"/>
  <p>Figure 14.9 Full-Screen Modal Dialog UI</p>
</div>

**UI Components**:

1. **Top bar**: Contains research topic and close button
2. **Progress area**: Shows current research progress (planning, execution, reporting)
3. **Content area**: Shows research results (Markdown format)
4. **Bottom bar**: Shows status information (such as "Researching...", "Completed")

The corresponding Vue implementation is as follows (ResearchModal.vue):

```vue
<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-container">
      <!-- Top bar -->
      <div class="modal-header">
        <h2>{{ researchTopic }}</h2>
        <button @click="close" class="close-button">
          <svg><!-- Close icon --></svg>
        </button>
      </div>

      <!-- Progress area -->
      <div class="progress-section">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progressPercentage + '%' }"
          ></div>
        </div>
        <div class="progress-text">{{ progressText }}</div>
      </div>

      <!-- Content area -->
      <div class="content-section">
        <div v-if="isLoading" class="loading-spinner">
          <div class="spinner"></div>
          <p>Researching, please wait...</p>
        </div>

        <div v-else class="markdown-content" v-html="renderedMarkdown"></div>
      </div>

      <!-- Bottom bar -->
      <div class="modal-footer">
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'

interface Props {
  isOpen: boolean
  researchTopic: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

// State
const isLoading = ref(true)
const progressPercentage = ref(0)
const progressText = ref('Preparing...')
const statusText = ref('Researching...')
const markdownContent = ref('')

// Render Markdown
const renderedMarkdown = computed(() => {
  return marked(markdownContent.value)
})

// Close modal
const close = () => {
  emit('close')
}

// Listen for ESC key
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    close()
  }
}

// Add keyboard listener on mount
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    document.addEventListener('keydown', handleKeydown)
  } else {
    document.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
...
</style>
```

To adapt to different screen sizes, we add media queries:

```css
/* Tablet devices */
@media (max-width: 768px) {
  .modal-container {
    width: 95vw;
    height: 95vh;
  }

  .modal-header,
  .progress-section,
  .content-section,
  .modal-footer {
    padding: 15px 20px;
  }
}

/* Mobile devices */
@media (max-width: 480px) {
  .modal-container {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }

  .modal-header h2 {
    font-size: 18px;
  }
}
```

### 14.6.2 Real-Time Progress Display

The deep research assistant uses SSE to implement real-time progress display. SSE is a server push technology that allows the server to actively send data to the client, which is also explained in the protocol chapter.

As shown in Figure 14.10, the SSE process includes the following steps:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-10.png" alt="" width="85%"/>
  <p>Figure 14.10 SSE Process</p>
</div>

**Process Description**:

1. **Client initiates request**: Send POST request to `/api/research`, containing research topic
2. **Server establishes SSE connection**: Return `text/event-stream` response
3. **Server pushes progress**: Periodically push research progress (planning, execution, reporting)
4. **Client receives progress**: Listen for SSE events, update UI
5. **Research complete**: Server pushes final report, closes connection

If you want to use SSE in front-end and back-end projects, you also need to make the following configurations.

**Back-End FastAPI SSE Endpoint**:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json

app = FastAPI()

async def research_stream(topic: str) -> AsyncGenerator[str, None]:
    """Research streaming generator

    Generate SSE format data:
    data: {"type": "progress", "data": {...}}

    """
    try:
        # 1. Planning stage
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'planning', 'percentage': 10, 'text': 'Planning research tasks...'})}\n\n"

        # Call PlanningService
        todo_items = await planning_service.plan_todo_list(topic)

        yield f"data: {json.dumps({'type': 'plan', 'data': [item.dict() for item in todo_items]})}\n\n"

        # 2. Execution stage
        task_summaries = []
        for idx, task in enumerate(todo_items, start=1):
            # Update progress
            percentage = 10 + (idx / len(todo_items)) * 70
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'executing', 'percentage': percentage, 'text': f'Researching task {idx}/{len(todo_items)}: {task.title}'})}\n\n"

            # Search
            search_results = await search_service.search(task.query)

            # Summarize
            summary, source_urls = await summarization_service.summarize_task(task, search_results)

            task_summaries.append((task, summary, source_urls))

            # Push task summary
            yield f"data: {json.dumps({'type': 'task_summary', 'task_id': task.id, 'summary': summary})}\n\n"

        # 3. Reporting stage
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'reporting', 'percentage': 90, 'text': 'Generating final report...'})}\n\n"

        # Generate report
        report = await reporting_service.generate_report(topic, task_summaries)

        # Push final report
        yield f"data: {json.dumps({'type': 'report', 'data': report})}\n\n"

        # Complete
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'completed', 'percentage': 100, 'text': 'Research complete!'})}\n\n"

    except Exception as e:
        # Error handling
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@app.post("/api/research")
async def research(request: ResearchRequest):
    """Research endpoint (SSE)"""
    return StreamingResponse(
        research_stream(request.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Front-End Using EventSource to Receive SSE**:

```typescript
// composables/useResearch.ts
import { ref } from 'vue'

export function useResearch() {
  const isLoading = ref(false)
  const progressPercentage = ref(0)
  const progressText = ref('')
  const markdownContent = ref('')
  const error = ref<string | null>(null)

  const startResearch = (topic: string) => {
    isLoading.value = true
    error.value = null

    // Create EventSource
    const eventSource = new EventSource(`/api/research?topic=${encodeURIComponent(topic)}`)

    // Listen for messages
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'progress':
          progressPercentage.value = data.percentage
          progressText.value = data.text
          break

        case 'plan':
          // Display planning results
          console.log('Planning results:', data.data)
          break

        case 'task_summary':
          // Append task summary to Markdown
          markdownContent.value += `\n\n## Task ${data.task_id}\n\n${data.summary}`
          break

        case 'report':
          // Display final report
          markdownContent.value = data.data
          break

        case 'error':
          error.value = data.message
          eventSource.close()
          isLoading.value = false
          break

        case 'completed':
          eventSource.close()
          isLoading.value = false
          break
      }
    }

    // Error handling
    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
      error.value = 'Connection failed, please retry'
      eventSource.close()
      isLoading.value = false
    }
  }

  return {
    isLoading,
    progressPercentage,
    progressText,
    markdownContent,
    error,
    startResearch,
  }
}
```

**Using in Component**:

```vue
<script setup lang="ts">
import { useResearch } from '@/composables/useResearch'

const {
  isLoading,
  progressPercentage,
  progressText,
  markdownContent,
  error,
  startResearch
} = useResearch()

const handleStartResearch = (topic: string) => {
  startResearch(topic)
}
</script>
```

### 14.6.3 Research Result Visualization

Research results are displayed in Markdown format, including titles, paragraphs, lists, quotes, and other elements. We use the `marked` library to convert Markdown to HTML and add custom styles.

**Rendering Markdown**:

```typescript
import { marked } from 'marked'

// Configure marked
marked.setOptions({
  breaks: true,  // Support line breaks
  gfm: true,     // Support GitHub Flavored Markdown
})

// Render
const renderedHtml = marked(markdownContent.value)
```

Research reports contain a large number of source citations, which we need to handle specially:

```markdown
## References

### Task 1: Basic Information about Datawhale
- [Datawhale GitHub](https://github.com/datawhalechina)
- [Datawhale Official Website](https://datawhale.club)

### Task 2: Main Projects of Datawhale
- [Hello-Agents Tutorial](https://github.com/datawhalechina/Hello-Agents)
...
```

Through full-screen modal dialog UI, SSE real-time progress display, and Markdown result visualization, we built a user-friendly front-end interface. Users can clearly see the research progress and view research results in a beautiful format.

## 14.7 Chapter Summary

In this chapter, we built a complete automated deep research agent system from scratch. Let's review the core points:

**(1) TODO-Driven Research Paradigm**

We proposed a new research paradigm - TODO-driven research. This paradigm decomposes complex research topics into executable subtasks and completes research through three stages:

- **Planning stage**: Decompose research topic into 3-5 subtasks, each subtask contains title, intent, and search query
- **Execution stage**: Execute search and summarization for each subtask, generating structured knowledge
- **Reporting stage**: Integrate summaries of all subtasks, generate final research report

The advantages of this paradigm are:

1. **Strong controllability**: Each subtask has clear objectives and scope
2. **Reliable quality**: Dedicated Agents ensure quality at each stage
3. **Easy to debug**: Can debug each subtask individually
4. **Good scalability**: Can easily add new subtasks or modify existing subtasks

**(2) Three-Agent Collaboration System**

We designed three specialized Agents, each performing their duties:

- **TODO Planner (Research Planning Expert)**: Responsible for decomposing research topics into subtasks
- **Task Summarizer (Task Summarization Expert)**: Responsible for summarizing search results for each subtask
- **Report Writer (Report Writing Expert)**: Responsible for integrating summaries of all subtasks and generating final report

The advantages of this design are:

1. **Clear responsibilities**: Each Agent focuses on a specific task
2. **Prompt optimization**: Can customize specialized Prompts for each Agent
3. **Easy to maintain**: Modifying one Agent does not affect other Agents
4. **Quality assurance**: Each Agent is an "expert" in their field

**(3) ToolAwareSimpleAgent Design**

We extended the `SimpleAgent` of the HelloAgents framework and implemented `ToolAwareSimpleAgent`. This Agent has tool call listening capability and can:

- **Listen to tool calls**: Listen to each tool call through callback functions
- **Real-time feedback**: Push tool call information to the front-end in real-time
- **Debugging support**: Record all tool calls for easy debugging

This Agent has been integrated into the HelloAgents framework and can be reused in other projects.

**(4) Tool System Integration**

We fully utilized the tool system of the HelloAgents framework:

- **SearchTool**: Extended to support more search engines (Tavily, DuckDuckGo, Perplexity, etc.)
- **NoteTool**: Persist research progress, support recovery and auditing
- **ToolRegistry**: Unified management of all tools, support custom extensions

Through configuration-based design, users can easily switch search engines without modifying code.

**(5) Core Service Implementation**

We implemented four core services connecting Agents and tools:

- **PlanningService**: Call planning Agent, parse JSON, validate format
- **SummarizationService**: Call summarization Agent, process search results, extract sources
- **ReportingService**: Call report Agent, integrate summaries, generate report
- **SearchService**: Schedule search engines, process results, error degradation, result caching

These services each perform their duties and collaborate through clear interfaces, achieving an automated process from research topic to final report.

**(6) Front-End Interaction Design**

We designed a user-friendly front-end interface:

- **Full-screen modal dialog**: Immersive experience, clear hierarchy
- **SSE real-time progress**: Real-time display of research progress, good user experience
- **Markdown visualization**: Beautiful format, clear structure

Through the Vue 3 + TypeScript + SSE technology stack, we implemented a modern web application.

This knowledge is not only applicable to deep research assistants, but can also be applied to other AI applications. We hope readers can explore more possibilities based on this chapter and build more powerful AI systems.

In the next chapter, we will build a multi-agent system combined with a game engine - Cyber Town, exploring complex interaction and collaboration patterns between Agents. Stay tuned!

