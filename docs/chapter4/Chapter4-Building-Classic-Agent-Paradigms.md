<div align="right">
  English | <a href="./第四章%20智能体经典范式构建.md">中文</a>
</div>

# Chapter 4: Building Classic Agent Paradigms

In the previous chapter, we deeply explored large language models as the "brain" of modern agents. We learned about their internal Transformer architecture, methods for interacting with them, and their capability boundaries. Now, it's time to transform this theoretical knowledge into practice and build agents with our own hands.

The core capability of a modern agent lies in its ability to connect the reasoning power of large language models with the external world. It can autonomously understand user intent, decompose complex tasks, and achieve goals by calling a series of "tools" such as code interpreters, search engines, and APIs to obtain information and execute operations. However, agents are not omnipotent; they also face challenges from the "hallucination" problem inherent in large models, potential reasoning loops in complex tasks, and incorrect tool usage, which constitute the capability boundaries of agents.

To better organize the "thinking" and "acting" processes of agents, the industry has emerged with multiple classic architectural paradigms. In this chapter, we will focus on the three most representative ones and implement them step by step from scratch:

- **ReAct (Reasoning and Acting):** A paradigm that tightly combines "thinking" and "acting," allowing agents to think while doing and dynamically adjust.
- **Plan-and-Solve:** A "think before you act" paradigm where agents first generate a complete action plan and then strictly execute it.
- **Reflection:** A paradigm that endows agents with "reflection" capabilities, optimizing results through self-criticism and correction.

After understanding these, you might ask: with many excellent frameworks like LangChain and LlamaIndex already available, why "reinvent the wheel"? The answer lies in the fact that although mature frameworks have significant advantages in engineering efficiency, directly using highly abstracted tools does not help us understand how the underlying design mechanisms work or what benefits they offer. Secondly, this process exposes engineering challenges in projects. Frameworks handle many issues for us, such as parsing model output formats, retrying failed tool calls, and preventing agents from falling into infinite loops. Handling these issues firsthand is the most direct way to cultivate system design capabilities. Finally, and most importantly, mastering design principles allows you to truly transform from a framework "user" to an intelligent application "creator." When standard components cannot meet your complex needs, you will have the ability to deeply customize or even build a completely new agent from scratch.

## 4.1 Environment Preparation and Basic Tool Definition

Before we start building, we need to set up the development environment and define some basic components. This will help us avoid repetitive work and focus more on core logic when implementing different paradigms later.

### 4.1.1 Installing Dependencies

The practical part of this book will mainly use the Python language, and Python 3.10 or higher is recommended. First, please ensure you have installed the `openai` library for interacting with large language models, and the `python-dotenv` library for securely managing our API keys.

Run the following command in your terminal:

```bash
pip install openai python-dotenv
```

### 4.1.2 Configuring API Keys

To make our code more universal, we will uniformly configure model service-related information (model ID, API key, service address) in environment variables.

1. In your project root directory, create a file named `.env`.
2. In this file, add the following content. You can point it to OpenAI's official service or any local/third-party service compatible with the OpenAI interface according to your needs.
3. If you really don't know how to obtain it, you can refer to Section [1.2 API Setup](https://datawhalechina.github.io/handy-multi-agent/#/chapter1/1.2.api-setup) in another Datawhale tutorial.

```bash
# .env file
LLM_API_KEY="YOUR-API-KEY"
LLM_MODEL_ID="YOUR-MODEL"
LLM_BASE_URL="YOUR-URL"
```

Our code will automatically load these configurations from this file.

### 4.1.3 Encapsulating Basic LLM Call Functions

To make the code structure clearer and more reusable, let's define a dedicated LLM client class. This class will encapsulate all details of interacting with model services, allowing our main logic to focus more on agent construction.

```python
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables from .env file
load_dotenv()

class HelloAgentsLLM:
    """
    A customized LLM client for the book "Hello Agents".
    It is used to call any service compatible with the OpenAI interface and uses streaming responses by default.
    """
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None, timeout: int = None):
        """
        Initialize the client. Prioritize passed parameters; if not provided, load from environment variables.
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))
        
        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("Model ID, API key, and service address must be provided or defined in the .env file.")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        Call the large language model to think and return its response.
        """
        print(f"🧠 Calling {self.model} model...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            # Handle streaming response
            print("✅ Large language model response successful:")
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()  # Newline after streaming output ends
            return "".join(collected_content)

        except Exception as e:
            print(f"❌ Error occurred when calling LLM API: {e}")
            return None

# --- Client Usage Example ---
if __name__ == '__main__':
    try:
        llmClient = HelloAgentsLLM()
        
        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "Write a quicksort algorithm"}
        ]
        
        print("--- Calling LLM ---")
        responseText = llmClient.think(exampleMessages)
        if responseText:
            print("\n\n--- Complete Model Response ---")
            print(responseText)

    except ValueError as e:
        print(e)


>>>
--- Calling LLM ---
🧠 Calling xxxxxx model...
✅ Large language model response successful:
Quicksort is a very efficient sorting algorithm...
```



## 4.2 ReAct

After preparing the LLM client, we will build the first and most classic agent paradigm: **ReAct (Reason + Act)**. ReAct was proposed by Shunyu Yao in 2022<sup>[1]</sup>. Its core idea is to mimic how humans solve problems by explicitly combining **Reasoning** and **Acting** to form a "think-act-observe" loop.

### 4.2.1 ReAct Workflow

Before ReAct emerged, mainstream methods could be divided into two categories: one is the "pure thinking" type, such as **Chain-of-Thought**, which can guide models to perform complex logical reasoning but cannot interact with the external world and is prone to factual hallucinations; the other is the "pure action" type, where models directly output actions to execute but lack planning and error correction capabilities.

The ingenuity of ReAct lies in recognizing that **thinking and acting are complementary**. Thinking guides action, while action results in turn correct thinking. To this end, the ReAct paradigm uses a special prompt engineering to guide the model so that each step of its output follows a fixed trajectory:

- **Thought (Thinking):** This is the agent's "inner monologue." It analyzes the current situation, decomposes tasks, formulates the next plan, or reflects on the results of the previous step.
- **Action (Acting):** This is the specific action the agent decides to take, usually calling an external tool, such as `Search['Huawei's latest phone']`.
- **Observation (Observing):** This is the result returned from the external tool after executing the `Action`, such as a summary of search results or an API return value.

The agent will continuously repeat this **Thought -> Action -> Observation** loop, appending new observation results to the history to form a continuously growing context until it determines in `Thought` that it has found the final answer and then outputs the result. This process forms a powerful synergy: **reasoning makes actions more purposeful, while actions provide factual basis for reasoning.**

We can formally express this process, as shown in Figure 4.1. Specifically, at each time step $t$, the agent's policy (i.e., the large language model $\pi$) generates the current thought $th_t$ and action $a_t$ based on the initial question $q$ and the historical trajectory of all previous "action-observation" steps $((a_1,o_1),\dots,(a_{t-1},o_{t-1}))$:

$$\left(th_t,a_t\right)=\pi\left(q,(a_1,o_1),\ldots,(a_{t-1},o_{t-1})\right)$$

Subsequently, the tool $T$ in the environment executes action $a_t$ and returns a new observation result $o_t$:

$$o_t = T(a_t)$$

This loop continues, appending new $(a_t,o_t)$ pairs to the history until the model determines in thought $th_t$ that the task is complete.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-1.png" alt="Think-Act-Observe synergistic loop in ReAct paradigm" width="90%"/>
  <p>Figure 4.1 Think-Act-Observe Synergistic Loop in ReAct Paradigm</p>
</div>

This mechanism is particularly suitable for the following scenarios:

- **Tasks requiring external knowledge**: Such as querying real-time information (weather, news, stock prices), searching for knowledge in professional domains, etc.
- **Tasks requiring precise calculations**: Delegating mathematical problems to calculator tools to avoid LLM calculation errors.
- **Tasks requiring API interaction**: Such as operating databases, calling a service's API to complete specific functions.

Therefore, we will build a ReAct agent with the capability to **use external tools** to answer questions that large language models cannot directly answer with their own knowledge base alone. For example: "What is Huawei's latest phone? What are its main selling points?" This question requires the agent to understand that it needs to search online, call tools to search for results, and summarize the answer.

### 4.2.2 Tool Definition and Implementation

If large language models are the brain of an agent, then **Tools** are its "hands and feet" for interacting with the external world. To enable the ReAct paradigm to truly solve the problems we set, the agent needs the capability to call external tools.

For the goal set in this section—answering questions about "Huawei's latest phone"—we need to provide the agent with a web search tool. Here we choose **SerpApi**, which provides structured Google search results through an API and can directly return "answer summary boxes" or precise knowledge graph information.

First, you need to install the library:

```bash
pip install google-search-results
```

At the same time, you need to go to the [SerpApi official website](https://serpapi.com/) to register a free account, obtain your API key, and add it to the `.env` file in our project root directory:

```bash
# .env file
# ... (Keep previous LLM configuration)
SERPAPI_API_KEY="YOUR_SERPAPI_API_KEY"
```

Next, we will define and manage this tool through code. We will proceed step by step: first implement the core functionality of the tool, then build a general tool manager.

(1) Implementing the Core Logic of the Search Tool

A well-defined tool should contain the following three core elements:

1. **Name**: A concise, unique identifier for the agent to call in `Action`, such as `Search`.
2. **Description**: A clear natural language description explaining the purpose of this tool. **This is the most critical part of the entire mechanism** because the large language model will rely on this description to determine when to use which tool.
3. **Execution Logic**: The function or method that actually performs the task.

Our first tool is the `search` function, which receives a query string and then returns search results.

```python
from serpapi import SerpApiClient

def search(query: str) -> str:
    """
    A practical web search engine tool based on SerpApi.
    It intelligently parses search results, prioritizing direct answers or knowledge graph information.
    """
    print(f"🔍 Executing [SerpApi] web search: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "Error: SERPAPI_API_KEY not configured in .env file."

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # Country code
            "hl": "zh-cn", # Language code
        }
        
        client = SerpApiClient(params)
        results = client.get_dict()
        
        # Intelligent parsing: prioritize finding the most direct answer
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # If no direct answer, return summaries of the first three organic results
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)
        
        return f"Sorry, no information found about '{query}'."

    except Exception as e:
        return f"Error occurred during search: {e}"
```

In the above code, it first checks whether `answer_box` (Google's answer summary box) or `knowledge_graph` (knowledge graph) information exists. If it does, it directly returns these most precise answers. If not, it falls back to returning summaries of the first three regular search results. This "intelligent parsing" can provide higher-quality information input for the LLM.

(2) Building a General Tool Executor

When an agent needs to use multiple tools (for example, in addition to search, it may also need calculation, database queries, etc.), we need a unified manager to register and dispatch these tools. For this, we create a `ToolExecutor` class.

```python
from typing import Dict, Any

class ToolExecutor:
    """
    A tool executor responsible for managing and executing tools.
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        Register a new tool in the toolbox.
        """
        if name in self.tools:
            print(f"Warning: Tool '{name}' already exists and will be overwritten.")
        self.tools[name] = {"description": description, "func": func}
        print(f"Tool '{name}' registered.")

    def getTool(self, name: str) -> callable:
        """
        Get a tool's execution function by name.
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        Get a formatted description string of all available tools.
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])

```

(3) Testing

Now, we will register the `search` tool in the `ToolExecutor` and simulate a call to verify that the entire process works properly.

```python
# --- Tool Initialization and Usage Example ---
if __name__ == '__main__':
    # 1. Initialize tool executor
    toolExecutor = ToolExecutor()

    # 2. Register our practical search tool
    search_description = "A web search engine. Use this tool when you need to answer questions about current events, facts, and information not found in your knowledge base."
    toolExecutor.registerTool("Search", search_description, search)

    # 3. Print available tools
    print("\n--- Available Tools ---")
    print(toolExecutor.getAvailableTools())

    # 4. Agent's Action call, this time we ask a real-time question
    print("\n--- Execute Action: Search['What is NVIDIA's latest GPU model'] ---")
    tool_name = "Search"
    tool_input = "What is NVIDIA's latest GPU model"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- Observation ---")
        print(observation)
    else:
        print(f"Error: Tool named '{tool_name}' not found.")

>>>
Tool 'Search' registered.

--- Available Tools ---
- Search: A web search engine. Use this tool when you need to answer questions about current events, facts, and information not found in your knowledge base.

--- Execute Action: Search['What is NVIDIA's latest GPU model'] ---
🔍 Executing [SerpApi] web search: What is NVIDIA's latest GPU model
--- Observation ---
[1] GeForce RTX 50 Series Graphics Cards
GeForce RTX™ 50 Series GPUs are powered by NVIDIA Blackwell architecture, bringing new gameplay for gamers and creators. RTX 50 Series has powerful AI computing power, bringing upgraded experience and more realistic graphics.

[2] Compare GeForce Series Latest Generation and Previous Generation Graphics Cards
Compare the latest RTX 30 series graphics cards with previous RTX 20 series, GTX 10 and 900 series graphics cards. View specifications, features, technical support, etc.

[3] GeForce Graphics Cards | NVIDIA
DRIVE AGX. Powerful in-vehicle computing power for AI-driven intelligent vehicle systems · Clara AGX. AI computing for innovative medical devices and imaging. Gaming and Creation. GeForce. Explore graphics cards, gaming solutions, AI ...
```

So far, we have equipped the agent with a `Search` tool that connects to the real-world internet, providing a solid foundation for the subsequent ReAct loop.



### 4.2.3 Coding Implementation of ReAct Agent

Now, we will assemble all independent components—the LLM client and tool executor—to build a complete ReAct agent. We will encapsulate its core logic through a `ReActAgent` class. For ease of understanding, we will break down the implementation process of this class into the following key parts for explanation.

(1) System Prompt Design

The prompt is the cornerstone of the entire ReAct mechanism, providing operational instructions for the large language model. We need to carefully design a template that will dynamically insert available tools, user questions, and the interaction history of intermediate steps.

```bash
# ReAct Prompt Template
REACT_PROMPT_TEMPLATE = """
Please note that you are an intelligent assistant capable of calling external tools.

Available tools are as follows:
{tools}

Please respond strictly in the following format:

Thought: Your thinking process, used to analyze problems, decompose tasks, and plan the next action.
Action: The action you decide to take, must be in one of the following formats:
- `{tool_name}[{tool_input}]`: Call an available tool.
- `Finish[final answer]`: When you believe you have obtained the final answer.
- When you have collected enough information to answer the user's final question, you must use `finish(answer="...")` after the Action: field to output the final answer.

Now, please start solving the following problem:
Question: {question}
History: {history}
"""
```

This template defines the specification for interaction between the agent and the LLM:

- **Role Definition**: "You are an intelligent assistant capable of calling external tools" sets the LLM's role.
- **Tool List (`{tools}`)**: Informs the LLM what "hands and feet" it has available.
- **Format Convention (`Thought`/`Action`)**: This is the most important part, forcing the LLM's output to be structured so we can precisely parse its intent through code.
- **Dynamic Context (`{question}`/`{history}`)**: Injects the user's original question and continuously accumulated interaction history, allowing the LLM to make decisions based on complete context.

(2) Core Loop Implementation

The core of `ReActAgent` is a loop that continuously "formats prompt -> calls LLM -> executes action -> integrates results" until the task is complete or the maximum step limit is reached.

```python
class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        """
        Run the ReAct agent to answer a question.
        """
        self.history = [] # Reset history for each run
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- Step {current_step} ---")

            # 1. Format prompt
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. Call LLM to think
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("Error: LLM failed to return a valid response.")
                break

            # ... (Subsequent parsing, execution, integration steps)

```

The `run` method is the entry point of the agent. Its `while` loop constitutes the main body of the ReAct paradigm, and the `max_steps` parameter is an important safety valve to prevent the agent from falling into an infinite loop and exhausting resources.

(3) Output Parser Implementation

The LLM returns plain text, and we need to precisely extract `Thought` and `Action` from it. This is accomplished through several auxiliary parsing functions, which typically use regular expressions.

```python
# (These methods are part of the ReActAgent class)
    def _parse_output(self, text: str):
        """Parse LLM output to extract Thought and Action."""
        thought_match = re.search(r"Thought: (.*)", text)
        action_match = re.search(r"Action: (.*)", text)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """Parse Action string to extract tool name and input."""
        match = re.match(r"(\w+)\[(.*)\]", action_text)
        if match:
            return match.group(1), match.group(2)
        return None, None
```

- `_parse_output`: Responsible for separating the two main parts `Thought` and `Action` from the LLM's complete response.
- `_parse_action`: Responsible for further parsing the `Action` string, for example, extracting the tool name `Search` and tool input `Huawei's latest phone` from `Search[Huawei's latest phone]`.

(4) Tool Invocation and Execution

```python
# (This logic is inside the while loop of the run method)
            # 3. Parse LLM output
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"Thought: {thought}")

            if not action:
                print("Warning: Failed to parse valid Action, process terminated.")
                break

            # 4. Execute Action
            if action.startswith("Finish"):
                # If it's a Finish instruction, extract the final answer and end
                final_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                print(f"🎉 Final Answer: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # ... Handle invalid Action format ...
                continue

            print(f"🎬 Action: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"Error: Tool named '{tool_name}' not found."
            else:
                observation = tool_function(tool_input) # Call real tool

```

This code is the execution center of `Action`. It first checks whether it's a `Finish` instruction; if so, the process ends. Otherwise, it obtains the corresponding tool function through `tool_executor` and executes it to get the `observation`.

(5) Integration of Observation Results

The last step, and the key to forming a closed loop, is to add the `Action` itself and the `Observation` after tool execution back to the history, providing new context for the next loop.

```python
# (This logic follows tool invocation, at the end of the while loop)
            print(f"👀 Observation: {observation}")

            # Add this round's Action and Observation to history
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # Loop ends
        print("Maximum steps reached, process terminated.")
        return None
```

By appending `Observation` to `self.history`, the agent can "see" the results of the previous action when generating the prompt in the next round, and conduct new thinking and planning accordingly.

(6) Running Instance and Analysis

Combining all the above parts, we get the complete `ReActAgent` class. The complete code running instance can be found in the `code` folder of this book's accompanying code repository.

Below is a real running record:

```
Tool 'Search' registered.

--- Step 1 ---
🧠 Calling xxxxxx model...
✅ Large language model response successful:
Thought: To answer this question, I need to search for Huawei's latest released phone model and its main features. This information may be outside my existing knowledge base, so I need to use a search engine to obtain the latest data.
Action: Search[Huawei latest phone model and main selling points]
🤔 Thought: To answer this question, I need to search for Huawei's latest released phone model and its main features. This information may be outside my existing knowledge base, so I need to use a search engine to obtain the latest data.
🎬 Action: Search[Huawei latest phone model and main selling points]
🔍 Executing [SerpApi] web search: Huawei latest phone model and main selling points
👀 Observation: [1] Huawei Phones - Huawei Official Website
Smartphones ; Mate Series. Extraordinary Flagship · HUAWEI Mate XTs. Extraordinary Master ; Pura Series. Pioneer Imaging · HUAWEI Pura 80 Pro+ ; Pocket Series. Aesthetic New Chapter. HUAWEI Pocket 2 ; nova Series. Professional Portrait.

[2] Which Huawei phone has the best value in 2025? Huawei phone recommendations and market analysis ...
Now the biggest selling point of Huawei phones is only the HarmonyOS system, and the controversial brand faith. Here are several Huawei series phones worth buying, choose according to different budgets:. Huawei's currently most popular, also equipped with ...

[3] Which new Huawei phone has the best value in 2025? 10 new Huawei phone recommendations
Choosing Huawei mainly recommends high-end phones, Mate 70 and Pura 70 series are the latest flagship models. HUAWEI Mate 70. Advantages are, photography configuration is still top-level, full focal length coverage, suitable for professional photography, excellent workmanship, outdoor drop resistance ...

--- Step 2 ---
🧠 Calling xxxxxx model...
✅ Large language model response successful:
Thought: Based on the search results, Huawei's latest flagship models include Mate 70 and Pura 80 Pro+. To determine the latest model and its main selling points, I will focus on this information. From the provided links, both Mate 70 series and Pura 80 Pro+ are recently released products, but which one is "latest" needs further confirmation. Meanwhile, I can extract their main selling points from this information.
Action: Finish[According to the latest information, Huawei's latest phones may be HUAWEI Pura 80 Pro+ or HUAWEI Mate 70. Among them, HUAWEI Mate 70's main selling points include top-level photography configuration, full focal length coverage, suitable for professional photography, excellent workmanship, and good outdoor drop resistance. While HUAWEI Pura 80 Pro+ emphasizes pioneer imaging technology.]
🤔 Thought: Based on the search results, Huawei's latest flagship models include Mate 70 and Pura 80 Pro+. To determine the latest model and its main selling points, I will focus on this information. From the provided links, both Mate 70 series and Pura 80 Pro+ are recently released products, but which one is "latest" needs further confirmation. Meanwhile, I can extract their main selling points from this information.
🎉 Final Answer: According to the latest information, Huawei's latest phones may be HUAWEI Pura 80 Pro+ or HUAWEI Mate 70. Among them, HUAWEI Mate 70's main selling points include top-level photography configuration, full focal length coverage, suitable for professional photography, excellent workmanship, and good outdoor drop resistance. While HUAWEI Pura 80 Pro+ emphasizes pioneer imaging technology.
```

From the above output, we can see that the agent clearly demonstrates its chain of thought: it first realizes its knowledge is insufficient and needs to use the search tool; then, it reasons and summarizes based on search results, arriving at the final answer within two steps.

It's worth noting that since the model's knowledge and internet information are constantly updated, your running results may not be exactly the same as this. As of September 8, 2025, when this section was written, the HUAWEI Mate 70 and HUAWEI Pura 80 Pro+ mentioned in search results were indeed Huawei's latest flagship series phones at that time. This fully demonstrates the powerful capability of the ReAct paradigm in handling time-sensitive issues.

### 4.2.4 Characteristics, Limitations, and Debugging Techniques of ReAct

By implementing a ReAct agent firsthand, we not only mastered its workflow but should also have a deeper understanding of its internal mechanisms. Any technical paradigm has its highlights and areas for improvement; this section will summarize ReAct.

(1) Main Characteristics of ReAct

1. **High Interpretability**: One of ReAct's greatest advantages is transparency. Through the `Thought` chain, we can clearly see the agent's "mental journey" at each step—why it chose this tool and what it plans to do next. This is crucial for understanding, trusting, and debugging agent behavior.
2. **Dynamic Planning and Error Correction Capability**: Unlike paradigms that generate complete plans at once, ReAct is "take one step, look one step." It dynamically adjusts subsequent `Thought` and `Action` based on `Observation` obtained from the external world at each step. If the previous search results are unsatisfactory, it can correct the search terms in the next step and try again.
3. **Tool Synergy Capability**: The ReAct paradigm naturally combines the reasoning capability of large language models with the execution capability of external tools. LLMs are responsible for strategizing (planning and reasoning), tools are responsible for solving specific problems (searching, calculating), and the two work synergistically, breaking through the inherent limitations of single LLMs in knowledge timeliness, computational accuracy, etc.

(2) Inherent Limitations of ReAct

1. **Strong Dependence on LLM's Own Capabilities**: The success of the ReAct process highly depends on the comprehensive capabilities of the underlying LLM. If the LLM's logical reasoning ability, instruction-following ability, or formatted output ability is insufficient, it's easy to produce wrong planning in the `Thought` stage or generate instructions that don't conform to the format in the `Action` stage, causing the entire process to be interrupted.
2. **Execution Efficiency Issues**: Due to its step-by-step nature, completing a task usually requires multiple LLM calls. Each call is accompanied by network latency and computational cost. For complex tasks requiring many steps, this serial "think-act" loop may lead to high total time and cost.
3. **Prompt Fragility**: The stable operation of the entire mechanism is built on a carefully designed prompt template. Any minor change in the template, even differences in wording, may affect LLM behavior. Additionally, not all models can consistently follow preset formats, increasing uncertainty in practical applications.
4. **May Fall into Local Optima**: The step-by-step decision-making mode means the agent lacks a global, long-term plan. It may choose a path that seems correct in the short term but is not optimal in the long run due to immediate `Observation`, or even fall into a "spinning in place" loop in some cases.

(3) Debugging Techniques

When your built ReAct agent behaves unexpectedly, you can debug from the following aspects:

- **Check Complete Prompt**: Before each LLM call, print out the final formatted complete prompt containing all history. This is the most direct way to trace the source of LLM decisions.
- **Analyze Raw Output**: When output parsing fails (for example, regular expressions didn't match `Action`), be sure to print out the raw, unprocessed text returned by the LLM. This can help you determine whether the LLM didn't follow the format or your parsing logic is wrong.
- **Verify Tool Input and Output**: Check whether the `tool_input` generated by the agent is in the format expected by the tool function, and also ensure the `observation` returned by the tool is in a format the agent can understand and process.
- **Adjust Examples in Prompt (Few-shot Prompting)**: If the model frequently makes errors, you can add one or two complete successful "Thought-Action-Observation" cases in the prompt to guide the model to better follow your instructions through examples.
- **Try Different Models or Parameters**: Switching to a more capable model or adjusting the `temperature` parameter (usually set to 0 to ensure output determinism) can sometimes directly solve the problem.

## 4.3 Plan-and-Solve

After mastering ReAct, this reactive, step-by-step decision-making agent paradigm, we will next explore a method with a very different style but equally powerful: **Plan-and-Solve**. As the name suggests, this paradigm explicitly divides task processing into two stages: **Plan first, then Solve**.

If ReAct is like an experienced detective who reasons step by step based on clues at the scene (Observation) and adjusts investigation direction at any time; then Plan-and-Solve is more like an architect who must first draw a complete blueprint (Plan) before starting construction, then strictly build according to the blueprint (Solve). In fact, many large model tools' Agent modes we use now incorporate this design pattern.

### 4.3.1 Working Principle of Plan-and-Solve

Plan-and-Solve Prompting was proposed by Lei Wang in 2023<sup>[2]</sup>. Its core motivation is to solve the problem that chain-of-thought easily "goes off track" when handling multi-step, complex problems.

Unlike ReAct, which integrates thinking and acting at each step, Plan-and-Solve decouples the entire process into two core stages, as shown in Figure 4.2:

1. **Planning Phase**: First, the agent receives the user's complete question. Its first task is not to directly solve the problem or call tools, but to **decompose the problem and formulate a clear, step-by-step action plan**. This plan itself is the product of a large language model call.
2. **Solving Phase**: After obtaining the complete plan, the agent enters the execution phase. It will **strictly execute according to the steps in the plan, one by one**. Each step's execution may be an independent LLM call or processing of the previous step's results, until all steps in the plan are completed and the final answer is obtained.

This "plan before acting" strategy enables the agent to maintain higher goal consistency when handling complex tasks requiring long-term planning, avoiding getting lost in intermediate steps.

We can formally express this two-stage process. First, the planning model $\pi_{\text{plan}}$ generates a plan $P = (p_1, p_2, \dots, p_n)$ containing $n$ steps based on the original question $q$:

$$
P = \pi_{\text{plan}}(q)
$$

Subsequently, in the execution phase, the execution model $\pi_{\text{solve}}$ will complete the steps in the plan one by one. For the $i$-th step, the generation of its solution $s_i$ will depend on the original question $q$, the complete plan $P$, and the execution results of all previous steps $(s_1, \dots, s_{i-1})$:

$$
s_i = \pi_{\text{solve}}(q, P, (s_1, \dots, s_{i-1}))
$$

The final answer is the execution result of the last step $s_n$.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-2.png" alt="Two-stage workflow of Plan-and-Solve paradigm" width="90%"/>
  <p>Figure 4.2 Two-Stage Workflow of Plan-and-Solve Paradigm</p>
</div>

Plan-and-Solve is especially suitable for complex tasks with strong structure that can be clearly decomposed, such as:

- **Multi-step math word problems**: Need to first list calculation steps, then solve one by one.
- **Report writing integrating multiple information sources**: Need to first plan the report structure (introduction, data source A, data source B, summary), then fill in content one by one.
- **Code generation tasks**: Need to first conceive the structure of functions, classes, and modules, then implement one by one.

### 4.3.2 Planning Phase

To highlight the advantages of the Plan-and-Solve paradigm in structured reasoning tasks, we will not use tools but complete a reasoning task through prompt design.

The characteristic of this type of task is that the answer cannot be obtained through a single query or calculation; the problem must first be decomposed into a series of logically coherent sub-steps, then solved in order. This precisely leverages Plan-and-Solve's core capability of "plan first, execute later."

**Our target problem is:** "A fruit store sold 15 apples on Monday. The number of apples sold on Tuesday was twice that of Monday. The number sold on Wednesday was 5 fewer than Tuesday. How many apples were sold in total over these three days?"

This problem is not particularly difficult for large language models, but it contains a clear logical chain for reference. For some actual logical puzzles, if the large model cannot reason out accurate answers with high quality, you can refer to this design pattern to design your own Agent to complete the task. The agent needs to:

1. **Planning Phase**: First, decompose the problem into three independent calculation steps (calculate Tuesday sales, calculate Wednesday sales, calculate total sales).
2. **Execution Phase**: Then, strictly follow the plan, execute calculations step by step, and use each step's result as input for the next step, finally obtaining the total.

The goal of the planning phase is to have the large language model receive the original problem and output a clear, step-by-step action plan. This plan must be structured so our code can easily parse and execute it one by one. Therefore, the prompt we design needs to clearly tell the model its role and task and provide an example of the output format.

````python
PLANNER_PROMPT_TEMPLATE = """
You are a top AI planning expert. Your task is to decompose complex problems posed by users into an action plan consisting of multiple simple steps.
Please ensure that each step in the plan is an independent, executable subtask and is strictly arranged in logical order.
Your output must be a Python list, where each element is a string describing a subtask.

Question: {question}

Please strictly output your plan in the following format, with ```python and ``` as prefix and suffix being necessary:
```python
["Step 1", "Step 2", "Step 3", ...]
```
"""
````

This prompt ensures output quality and stability through the following points:
- **Role Setting**: "Top AI planning expert" activates the model's professional capabilities.
- **Task Description**: Clearly defines the goal of "decomposing problems."
- **Format Constraint**: Forces output to be a string in Python list format, which greatly simplifies subsequent code parsing work, making it more stable and reliable than parsing natural language.

Next, we encapsulate this prompt logic into a `Planner` class, which is also our planner.

```python
# Assume the HelloAgentsLLM class in llm_client.py is already defined
# from llm_client import HelloAgentsLLM

class Planner:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """
        Generate an action plan based on user question.
        """
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)

        # To generate a plan, we build a simple message list
        messages = [{"role": "user", "content": prompt}]

        print("--- Generating Plan ---")
        # Use streaming output to get the complete plan
        response_text = self.llm_client.think(messages=messages) or ""

        print(f"✅ Plan Generated:\n{response_text}")

        # Parse the list string output by LLM
        try:
            # Find content between ```python and ```
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            # Use ast.literal_eval to safely execute the string and convert it to a Python list
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ Error parsing plan: {e}")
            print(f"Raw response: {response_text}")
            return []
        except Exception as e:
            print(f"❌ Unknown error occurred while parsing plan: {e}")
            return []
```

### 4.3.3 Executor and State Management

After the planner (`Planner`) generates a clear action blueprint, we need an executor (`Executor`) to complete the tasks in the plan one by one. The executor is not only responsible for calling the large language model to solve each sub-problem but also plays a crucial role: **state management**. It must record the execution results of each step and provide them as context for subsequent steps, ensuring information flows smoothly throughout the entire task chain.

The executor's prompt is different from the planner's. Its goal is not to decompose problems but to **focus on solving the current step based on existing context**. Therefore, the prompt needs to include the following key information:

- **Original Question**: Ensure the model always understands the ultimate goal.
- **Complete Plan**: Let the model understand the current step's position in the entire task.
- **Historical Steps and Results**: Provide work completed so far as direct input for the current step.
- **Current Step**: Clearly instruct the model which specific task it needs to solve now.

```python
EXECUTOR_PROMPT_TEMPLATE = """
You are a top AI execution expert. Your task is to strictly follow the given plan and solve the problem step by step.
You will receive the original question, the complete plan, and the steps and results completed so far.
Please focus on solving the "current step" and only output the final answer for that step, without any additional explanations or dialogue.

# Original Question:
{question}

# Complete Plan:
{plan}

# Historical Steps and Results:
{history}

# Current Step:
{current_step}

Please only output the answer for the "current step":
"""
```

We encapsulate the execution logic into the `Executor` class. This class will loop through the plan, call the LLM, and maintain a history (state).

```python
class Executor:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, question: str, plan: list[str]) -> str:
        """
        Execute step by step according to the plan and solve the problem.
        """
        history = "" # String to store historical steps and results

        print("\n--- Executing Plan ---")

        for i, step in enumerate(plan):
            print(f"\n-> Executing step {i+1}/{len(plan)}: {step}")

            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "None", # If it's the first step, history is empty
                current_step=step
            )

            messages = [{"role": "user", "content": prompt}]

            response_text = self.llm_client.think(messages=messages) or ""

            # Update history for the next step
            history += f"Step {i+1}: {step}\nResult: {response_text}\n\n"

            print(f"✅ Step {i+1} completed, result: {response_text}")

        # After the loop ends, the last step's response is the final answer
        final_answer = response_text
        return final_answer
```

Now we have separately built the `Planner` responsible for "planning" and the `Executor` responsible for "execution." The last step is to integrate these two components into a unified agent `PlanAndSolveAgent` and give it complete problem-solving capabilities. We will create a main class `PlanAndSolveAgent` whose responsibility is very clear: receive an LLM client, initialize internal planner and executor, and provide a simple `run` method to start the entire process.

```python
class PlanAndSolveAgent:
    def __init__(self, llm_client):
        """
        Initialize the agent and create planner and executor instances.
        """
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client)

    def run(self, question: str):
        """
        Run the agent's complete process: plan first, then execute.
        """
        print(f"\n--- Starting to Process Question ---\nQuestion: {question}")

        # 1. Call planner to generate plan
        plan = self.planner.plan(question)

        # Check if plan was successfully generated
        if not plan:
            print("\n--- Task Terminated --- \nUnable to generate valid action plan.")
            return

        # 2. Call executor to execute plan
        final_answer = self.executor.execute(question, plan)

        print(f"\n--- Task Completed ---\nFinal Answer: {final_answer}")
```

The design of this `PlanAndSolveAgent` class embodies the principle of "composition over inheritance." It doesn't contain complex logic itself but acts as an orchestrator, clearly calling its internal components to complete tasks.

### 4.3.4 Running Instance and Analysis

The complete code can also be found in the `code` folder of this book's accompanying code repository; here we only demonstrate the final results.

````bash
--- Starting to Process Question ---
Question: A fruit store sold 15 apples on Monday. The number of apples sold on Tuesday was twice that of Monday. The number sold on Wednesday was 5 fewer than Tuesday. How many apples were sold in total over these three days?
--- Generating Plan ---
🧠 Calling xxxx model...
✅ Large language model response successful:
```python
["Calculate Monday's apple sales: 15", "Calculate Tuesday's apple sales: Monday's quantity × 2 = 15 × 2 = 30", "Calculate Wednesday's apple sales: Tuesday's quantity - 5 = 30 - 5 = 25", "Calculate total sales for three days: Monday + Tuesday + Wednesday = 15 + 30 + 25 = 70"]
```
✅ Plan Generated:
```python
["Calculate Monday's apple sales: 15", "Calculate Tuesday's apple sales: Monday's quantity × 2 = 15 × 2 = 30", "Calculate Wednesday's apple sales: Tuesday's quantity - 5 = 30 - 5 = 25", "Calculate total sales for three days: Monday + Tuesday + Wednesday = 15 + 30 + 25 = 70"]
```

--- Executing Plan ---

-> Executing step 1/4: Calculate Monday's apple sales: 15
🧠 Calling xxxx model...
✅ Large language model response successful:
15
✅ Step 1 completed, result: 15

-> Executing step 2/4: Calculate Tuesday's apple sales: Monday's quantity × 2 = 15 × 2 = 30
🧠 Calling xxxx model...
✅ Large language model response successful:
30
✅ Step 2 completed, result: 30

-> Executing step 3/4: Calculate Wednesday's apple sales: Tuesday's quantity - 5 = 30 - 5 = 25
🧠 Calling xxxx model...
✅ Large language model response successful:
25
✅ Step 3 completed, result: 25

-> Executing step 4/4: Calculate total sales for three days: Monday + Tuesday + Wednesday = 15 + 30 + 25 = 70
🧠 Calling xxxx model...
✅ Large language model response successful:
70
✅ Step 4 completed, result: 70

--- Task Completed ---
Final Answer: 70
````

From the above output log, we can clearly see the workflow of the Plan-and-Solve paradigm:

1. **Planning Phase**: The agent first calls `Planner` and successfully decomposes the complex word problem into a Python list containing four logical steps. This structured plan lays the foundation for subsequent execution.
2. **Execution Phase**: `Executor` strictly executes step by step according to the generated plan. In each step, it uses historical results as context, ensuring correct information transfer (for example, step 2 correctly uses step 1's result "15", and step 3 also correctly uses step 2's result "30").
3. **Result**: The entire process is logically clear with explicit steps, and the agent accurately arrives at the correct answer "70".

## 4.4 Reflection

In the ReAct and Plan-and-Solve paradigms we have already implemented, once the agent completes a task, its workflow ends. However, the initial answers they generate, whether action trajectories or final results, may contain errors or have room for improvement. The core idea of the Reflection mechanism is to introduce a **post-hoc self-correction loop** for the agent, enabling it to review its work, discover deficiencies, and iteratively optimize, just like humans do.

### 4.4.1 Core Idea of Reflection Mechanism

The inspiration for the Reflection mechanism comes from the human learning process: we proofread after completing a first draft and verify after solving a math problem. This idea is embodied in multiple studies, such as the Reflexion framework proposed by Shinn, Noah in 2023<sup>[3]</sup>. Its core workflow can be summarized as a concise three-step loop: **Execute -> Reflect -> Refine**.

1. **Execution**: First, the agent attempts to complete the task using familiar methods (such as ReAct or Plan-and-Solve), generating a preliminary solution or action trajectory. This can be seen as a "first draft."
2. **Reflection**: Next, the agent enters the reflection phase. It calls an independent large language model instance, or one with special prompts, to play the role of a "reviewer." This "reviewer" examines the "first draft" generated in the first step and evaluates it from multiple dimensions, such as:
   - **Factual Errors**: Is there content that contradicts common sense or known facts?
   - **Logical Flaws**: Are there inconsistencies or contradictions in the reasoning process?
   - **Efficiency Issues**: Is there a more direct, more concise path to complete the task?
   - **Missing Information**: Are some key constraints or aspects of the problem overlooked? Based on the evaluation, it generates structured **Feedback**, pointing out specific problems and improvement suggestions.
3. **Refinement**: Finally, the agent uses the "first draft" and "feedback" as new context, calls the large language model again, and asks it to revise the first draft based on the feedback content, generating a more complete "revised draft."

As shown in Figure 4.3, this loop can be repeated multiple times until the reflection phase no longer finds new problems or reaches a preset iteration limit. We can formally express this iterative optimization process. Assuming $O_i$ is the output produced by the $i$-th iteration ($O_0$ is the initial output), the reflection model $\pi_{\text{reflect}}$ generates feedback $F_i$ for $O_i$:
$$
F_i = \pi_{\text{reflect}}(\text{Task}, O_i)
$$
Subsequently, the refinement model $\pi_{\text{refine}}$ combines the original task, the previous version's output, and feedback to generate a new version's output $O_{i+1}$:
$$
O_{i+1} = \pi_{\text{refine}}(\text{Task}, O_i, F_i)
$$



<div align="center">
<img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-3.png" alt="Execute-Reflect-Refine iterative loop in Reflection mechanism" width="70%"/>
<p>Figure 4.3 Execute-Reflect-Refine Iterative Loop in Reflection Mechanism</p>
</div>



Compared to the previous two paradigms, the value of Reflection lies in:

- It provides the agent with an internal error correction loop, making it no longer completely dependent on external tool feedback (ReAct's Observation), thus able to correct higher-level logical and strategic errors.
- It transforms one-time task execution into a continuous optimization process, significantly improving the final success rate and answer quality for complex tasks.
- It builds a temporary **"short-term memory"** for the agent. The entire "execute-reflect-refine" trajectory forms a valuable experience record; the agent not only knows the final answer but also remembers how it iterated from a flawed first draft to the final version. Furthermore, this memory system can also be **multimodal**, allowing the agent to reflect on and revise outputs beyond text (such as code, images, etc.), laying the foundation for building more powerful multimodal agents.

### 4.4.2 Case Setting and Memory Module Design

To embody the Reflection mechanism in practice, we will introduce a memory management mechanism, because reflection usually corresponds to information storage and retrieval. If the context is long enough, having the "reviewer" directly obtain all information and then reflect often introduces a lot of redundant information. In this practical step, we mainly complete **code generation and iterative optimization**.

The goal task for this step is: "Write a Python function to find all prime numbers between 1 and n."

This task is an excellent scenario for testing the Reflection mechanism:

1. **Clear Optimization Path Exists**: The code initially generated by the large language model is likely a simple but inefficient recursive implementation.
2. **Clear Reflection Points**: Through reflection, problems like "excessively high time complexity" or "redundant calculations" can be discovered.
3. **Clear Optimization Direction**: Based on feedback, it can be optimized to a more efficient iterative version or a version using the memoization pattern.

The core of Reflection lies in iteration, and the prerequisite for iteration is the ability to remember previous attempts and received feedback. Therefore, a "short-term memory" module is essential for implementing this paradigm. This memory module will be responsible for storing the complete trajectory of each "execute-reflect" loop.

```python
from typing import List, Dict, Any, Optional

class Memory:
    """
    A simple short-term memory module for storing the agent's action and reflection trajectory.
    """

    def __init__(self):
        """
        Initialize an empty list to store all records.
        """
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        """
        Add a new record to memory.

        Parameters:
        - record_type (str): Type of record ('execution' or 'reflection').
        - content (str): Specific content of the record (e.g., generated code or reflection feedback).
        """
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"📝 Memory updated, added a '{record_type}' record.")

    def get_trajectory(self) -> str:
        """
        Format all memory records into a coherent string text for building prompts.
        """
        trajectory_parts = []
        for record in self.records:
            if record['type'] == 'execution':
                trajectory_parts.append(f"--- Previous Attempt (Code) ---\n{record['content']}")
            elif record['type'] == 'reflection':
                trajectory_parts.append(f"--- Reviewer Feedback ---\n{record['content']}")

        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> Optional[str]:
        """
        Get the most recent execution result (e.g., the latest generated code).
        Returns None if it doesn't exist.
        """
        for record in reversed(self.records):
            if record['type'] == 'execution':
                return record['content']
        return None
```

The design of this `Memory` class is relatively concise, with the main structure as follows:

- Uses a list `records` to store each action and reflection in order.
- The `add_record` method is responsible for adding new entries to memory.
- The `get_trajectory` method is the core; it "serializes" the memory trajectory into a text segment that can be directly inserted into subsequent prompts, providing complete context for the model's reflection and optimization.
- `get_last_execution` makes it convenient to obtain the latest "first draft" for reflection.



### 4.4.3 Coding Implementation of Reflection Agent

With the `Memory` module as a foundation, we can now proceed to build the core logic of `ReflectionAgent`. The entire agent's workflow will revolve around the "execute-reflect-refine" loop we discussed earlier and guide the large language model to play different roles through carefully designed prompts.

(1) Prompt Design

Unlike previous paradigms, the Reflection mechanism requires multiple prompts for different roles to work together.

1. **Initial Execution Prompt**: This is the prompt for the agent's first attempt to solve the problem, with relatively straightforward content, only requiring the model to complete the specified task.

```bash
INITIAL_PROMPT_TEMPLATE = """
You are a senior Python programmer. Please write a Python function according to the following requirements.
Your code must include a complete function signature, docstring, and follow PEP 8 coding standards.

Requirement: {task}

Please output the code directly without any additional explanations.
"""
```

2. **Reflection Prompt**: This prompt is the soul of the Reflection mechanism. It instructs the model to play the role of a "code reviewer," critically analyze the code generated in the previous round, and provide specific, actionable feedback.

````bash
REFLECT_PROMPT_TEMPLATE = """
You are an extremely strict code review expert and senior algorithm engineer with ultimate requirements for code performance.
Your task is to review the following Python code and focus on finding its main bottlenecks in <strong>algorithm efficiency</strong>.

# Original Task:
{task}

# Code to Review:
```python
{code}
```

Please analyze the time complexity of this code and consider whether there is an <strong>algorithmically superior</strong> solution to significantly improve performance.
If one exists, please clearly point out the deficiencies of the current algorithm and propose specific, feasible algorithm improvement suggestions (e.g., using sieve method instead of trial division).
Only if the code has reached optimality at the algorithm level can you answer "no improvement needed."

Please output your feedback directly without any additional explanations.
"""
````

3. **Refinement Prompt**: After receiving feedback, this prompt will guide the model to revise and optimize the original code based on the feedback content.

````bash

REFINE_PROMPT_TEMPLATE = """
You are a senior Python programmer. You are optimizing your code based on feedback from a code review expert.

# Original Task:
{task}

# Your Previous Code Attempt:
```
{last_code_attempt}
Reviewer's Feedback:
{feedback}

Please generate an optimized new version of the code based on the reviewer's feedback.
Your code must include a complete function signature, docstring, and follow PEP 8 coding standards.
Please output the optimized code directly without any additional explanations.
"""
````

(2) Agent Encapsulation and Implementation

Now, we will integrate this set of prompt logic and the `Memory` module into the `ReflectionAgent` class.

```python
# Assume llm_client.py and memory.py are already defined
# from llm_client import HelloAgentsLLM
# from memory import Memory

class ReflectionAgent:
    def __init__(self, llm_client, max_iterations=3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str):
        print(f"\n--- Starting to Process Task ---\nTask: {task}")

        # --- 1. Initial Execution ---
        print("\n--- Performing Initial Attempt ---")
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution", initial_code)

        # --- 2. Iterative Loop: Reflection and Refinement ---
        for i in range(self.max_iterations):
            print(f"\n--- Iteration {i+1}/{self.max_iterations} ---")

            # a. Reflection
            print("\n-> Performing Reflection...")
            last_code = self.memory.get_last_execution()
            reflect_prompt = REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            self.memory.add_record("reflection", feedback)

            # b. Check if stopping is needed
            if "no improvement needed" in feedback.lower():
                print("\n✅ Reflection considers code needs no improvement, task completed.")
                break

            # c. Refinement
            print("\n-> Performing Refinement...")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(
                task=task,
                last_code_attempt=last_code,
                feedback=feedback
            )
            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()
        print(f"\n--- Task Completed ---\nFinal Generated Code:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str) -> str:
        """A helper method for calling LLM and getting complete streaming response."""
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        return response_text

```

### 4.4.4 Running Instance and Analysis

The complete code can also be found in the `code` folder of this book's accompanying code repository; here we provide an output instance.

````python
--- Starting to Process Task ---
Task: Write a Python function to find all prime numbers between 1 and n.

--- Performing Initial Attempt ---
🧠 Calling xxxxxx model...
✅ Large language model response successful:
```python
def find_primes(n):
    ...
    return primes
```
📝 Memory updated, added an 'execution' record.

--- Iteration 1/2 ---

-> Performing Reflection...
🧠 Calling xxxxxx model...
✅ Large language model response successful:
The current code has a time complexity of O(n * sqrt(n)). While this implementation is acceptable for smaller n values, performance will significantly degrade when n is very large. The main bottleneck is that each number needs trial division checking, leading to high time overhead.

It is recommended to use the Sieve of Eratosthenes algorithm, which has a time complexity of O(n log(log n)) and can significantly improve the efficiency of finding prime numbers.

Improved code as follows:
```python
def find_primes(n):
    ...
    return primes
```
📝 Memory updated, added a 'reflection' record.

-> Performing Refinement...
🧠 Calling xxxxxx model...
✅ Large language model response successful:
```python
def find_primes(n):
    ...
    return primes
```
📝 Memory updated, added an 'execution' record.

--- Iteration 2/2 ---

-> Performing Reflection...
🧠 Calling xxxxxx model...
✅ Large language model response successful:
The current code uses the Sieve of Eratosthenes with time complexity O(n log log n) and space complexity O(n). This algorithm is already very efficient for finding all prime numbers between 1 and n, and usually requires no further optimization. However, in some specific scenarios, the following improvements can be considered:

1. <strong>Segmented Sieve</strong>: Suitable for cases where n is very large but memory is limited. Divide the interval into multiple small segments, process each segment separately with the sieve method, reducing memory usage.
2. <strong>Odd Number Sieve</strong>: Except for 2, all prime numbers are odd. When initializing the `is_prime` array, only mark odd numbers, which can reduce space complexity by half while reducing some unnecessary calculations.

However, these improvements are not necessary for most application scenarios because the standard Sieve of Eratosthenes is already efficient enough. Therefore, in general cases, <strong>no improvement needed</strong>.
📝 Memory updated, added a 'reflection' record.

✅ Reflection considers code needs no improvement, task completed.

--- Task Completed ---
Final Generated Code:
```python
def find_primes(n):
    """
    Finds all prime numbers between 1 and n using the Sieve of Eratosthenes algorithm.

    :param n: The upper limit of the range to find prime numbers.
    :return: A list of all prime numbers between 1 and n.
    """
    if n < 2:
        return []

    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False

    p = 2
    while p * p <= n:
        if is_prime[p]:
            for i in range(p * p, n + 1, p):
                is_prime[i] = False
        p += 1

    primes = [num for num in range(2, n + 1) if is_prime[num]]
    return primes
```
````

This running instance demonstrates how the Reflection mechanism drives the agent to perform deep optimization:

1. **Effective "Criticism" is the Prerequisite for Optimization**: In the first round of reflection, because we used an "extremely strict" and "focused on algorithm efficiency" prompt, the agent was not satisfied with the functionally correct initial code but precisely pointed out its `O(n * sqrt(n))` time complexity bottleneck and proposed algorithm-level improvement suggestions—the Sieve of Eratosthenes.
2. **Iterative Improvement**: After receiving clear feedback, the agent successfully implemented a more efficient sieve method in the refinement phase, reducing algorithm complexity to `O(n log log n)`, completing the first meaningful self-iteration.
3. **Convergence and Termination**: In the second round of reflection, facing the already efficient sieve method, the agent demonstrated deeper knowledge. It not only affirmed the current algorithm's efficiency but even mentioned more advanced optimization directions like segmented sieve, but ultimately made the correct judgment of "no improvement needed in general cases." This judgment triggered our termination condition, allowing the optimization process to converge.

This case fully proves that a well-designed Reflection mechanism's value lies not only in fixing errors but more importantly in **driving solutions to achieve step-wise improvements in quality and efficiency**, making it one of the key technologies for building complex, high-quality agents.

### 4.4.5 Cost-Benefit Analysis of Reflection Mechanism

Although the Reflection mechanism performs excellently in improving task solution quality, this capability is not without cost. In practical applications, we need to weigh the benefits it brings against the corresponding costs.

(1) Main Costs

1. **Increased Model Call Overhead**: This is the most direct cost. Each iteration requires at least two additional large language model calls (one for reflection, one for refinement). If iterating multiple rounds, API call costs and computational resource consumption will increase exponentially.

2. **Significantly Increased Task Latency**: Reflection is a serial process; each round of refinement must wait for the previous round's reflection to complete. This significantly extends the total task time, making it unsuitable for scenarios with high real-time requirements.

3. **Increased Prompt Engineering Complexity**: As our case demonstrates, the success of Reflection largely depends on high-quality, targeted prompts. Designing and debugging effective prompts for different stages like "execution," "reflection," and "refinement" requires more development effort.

(2) Core Benefits

1. **Leap in Solution Quality**: The greatest benefit is that it can iteratively optimize a "qualified" initial solution into an "excellent" final solution. This improvement from functionally correct to performance-efficient, from rough logic to rigorous logic, is crucial in many critical tasks.

2. **Enhanced Robustness and Reliability**: Through internal self-correction loops, the agent can discover and fix potential logical flaws, factual errors, or improper boundary case handling in the initial solution, greatly improving the reliability of the final result.

In summary, the Reflection mechanism is a typical "cost for quality" strategy. It is very suitable for scenarios that **have extremely high requirements for the quality, accuracy, and reliability of final results, and have relatively relaxed requirements for task completion real-time performance**. For example:

- Generating critical business code or technical reports.
- Conducting complex logical reasoning in scientific research.
- Decision support systems requiring deep analysis and planning.

Conversely, if the application scenario requires quick responses, or a "roughly correct" answer is already sufficient, using lighter ReAct or Plan-and-Solve paradigms may be a more cost-effective choice.

## 4.5 Chapter Summary

In this chapter, building on the large language model knowledge mastered in Chapter 3, we coded and implemented three classic industry agent construction paradigms from scratch through "building wheels ourselves": ReAct, Plan-and-Solve, and Reflection. We not only explored their core working principles but also deeply understood their respective advantages, limitations, and applicable scenarios through specific practical cases.

**Core Knowledge Review:**

1. ReAct: We built a ReAct agent that can interact with the external world. Through the dynamic loop of "thought-action-observation," it successfully used search engines to answer real-time questions that its own knowledge base couldn't cover. Its core advantages lie in **environmental adaptability** and **dynamic error correction capability**, making it the first choice for handling exploratory tasks requiring external tool input.
2. Plan-and-Solve: We implemented a Plan-and-Solve agent that plans first then executes, and used it to solve math word problems requiring multi-step reasoning. It decomposes complex tasks into clear steps, then executes them one by one. Its core advantages lie in **structure** and **stability**, particularly suitable for handling tasks with determined logical paths and intensive internal reasoning.
3. Reflection (Self-Reflection and Iteration): We built a Reflection agent with self-optimization capabilities. By introducing the "execute-reflect-refine" iterative loop, it successfully optimized an initially inefficient code solution into an algorithmically superior high-performance version. Its core value lies in **significantly improving solution quality**, suitable for scenarios with extremely high requirements for result accuracy and reliability.

The three paradigms explored in this chapter represent three different strategies for agents to solve problems, as shown in Table 4.1. In practical applications, which one to choose depends on the core requirements of the task:

<div align="center">
<p>Table 4.1 Selection Strategy for Different Agent Loops</p>
<img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-4.png" alt="" width="70%"/>
</div>

At this point, we have mastered the core technologies for building individual agents. To transition knowledge and gain deeper insights into practical applications, in the next section we will explore how to use different low-code platforms and lightweight code solutions for building agents.

## Exercises

> **Note**: Some exercises do not have standard answers; the focus is on cultivating learners' comprehensive understanding and practical ability in agent paradigm design.

1. This chapter introduced three classic agent paradigms: `ReAct`, `Plan-and-Solve`, and `Reflection`. Please analyze:

   - What are the essential differences in how these three paradigms organize "thinking" and "action"?
   - If you were to design a "smart home control assistant" (needs to control lights, air conditioning, curtains, and other devices, and automatically adjust based on user habits), which paradigm would you choose as the basic architecture? Why?
   - Can these three paradigms be combined? If so, please try to design a hybrid paradigm agent architecture and explain its applicable scenarios.

2. In the `ReAct` implementation in Section 4.2, we used regular expressions to parse the large language model's output (such as `Thought` and `Action`). Please consider:

   - What potential fragilities exist in the current parsing method? Under what circumstances might it fail?
   - Besides regular expressions, what are some more robust output parsing solutions?
   - Try modifying the code in this chapter to use a more reliable output format, and compare the pros and cons of the two approaches.

3. Tool invocation is one of the core capabilities of modern agents. Based on the `ToolExecutor` design in Section 4.2.2, please complete the following extension practice:

   > **Note**: This is a hands-on practice question; it is recommended to actually write code.

   - Add a "calculator" tool to the `ReAct` agent so it can handle complex mathematical calculation problems (such as "Calculate the result of `(123 + 456) × 789 / 12 = ?`").
   - Design and implement a "tool selection failure" handling mechanism: when the agent repeatedly calls the wrong tool or provides wrong parameters, how should the system guide it to correct?
   - Consider: If the number of callable tools increases to 50 or even 100, will the current tool description method still work effectively? From an engineering perspective, how can we optimize the organization and retrieval mechanism of tools when the number of callable tools significantly increases with business needs?

4. The `Plan-and-Solve` paradigm decomposes tasks into two stages: "planning" and "execution." Please analyze in depth:

   - In the implementation in Section 4.3, the plan generated in the planning phase is "static" (generated once, not modifiable). If during execution it is found that a certain step cannot be completed or the result does not meet expectations, how should a "dynamic replanning" mechanism be designed?
   - Compare `Plan-and-Solve` with `ReAct`: When handling a task like "booking a business trip from Beijing to Shanghai (including flights, hotels, car rental)," which paradigm is more suitable? Why?
   - Try designing a "hierarchical planning" system: first generate a high-level abstract plan, then generate detailed sub-plans for each high-level step. What advantages does this design have?

5. The `Reflection` mechanism improves output quality through the "execute-reflect-refine" loop. Please consider:

   - In the code generation case in Section 4.4, the same model is used for different stages. If two different models are used (for example, using a more powerful model for reflection and a faster model for execution), what impact would it have?
   - The termination condition for the `Reflection` mechanism is "feedback contains **no improvement needed**" or "maximum iteration count reached." Is this design reasonable? Can a more intelligent termination condition be designed?
   - Suppose you want to build an "academic paper writing assistant" that can generate drafts and continuously optimize paper content. Please design a multi-dimensional Reflection mechanism that reflects and improves from multiple perspectives such as paragraph logic, method innovation, language expression, and citation standards.

6. Prompt engineering is a key technology affecting the final effect of agents. This chapter demonstrated multiple carefully designed prompt templates. Please analyze:

   - Compare the `ReAct` prompt in Section 4.2.3 and the `Plan-and-Solve` prompt in Section 4.3.2; they obviously have significant differences in structural design. How do these differences serve the core logic of their respective paradigms?
   - In the `Reflection` prompt in Section 4.4.3, we used a role setting like "you are an extremely strict code review expert." Try modifying this role setting (such as changing it to "you are an open-source project maintainer who values code readability"), observe the changes in output results, and summarize the impact of role settings on agent behavior.
   - Adding `few-shot` examples to prompts can often significantly improve the model's ability to follow specific formats. Please try adding `few-shot` examples to one of the agents in this chapter and compare the effects.

7. An e-commerce startup now hopes to use a "customer service agent" to replace human customer service for cost reduction and efficiency improvement. It needs to have the following functions:

   a. Understand the user's refund request reason

   b. Query the user's order information and logistics status

   c. Intelligently judge whether the refund should be approved based on company policy

   d. Generate a proper reply email and send it to the user's email

   e. If the judgment decision is somewhat controversial (self-confidence is below a threshold), be able to self-reflect and provide more prudent suggestions

   As the product manager of this product:
   - Which paradigm (or combination of paradigms) from this chapter would you choose as the core architecture of the system?
   - What tools does this system need? Please list at least 3 tools and their functional descriptions.
   - How to design prompts to ensure that the agent's decisions both align with company interests and maintain a friendly attitude toward users?
   - What risks and challenges might this product face after launch? How can these risks be reduced through technical means?

## References

[1] Yao S, Zhao J, Yu D, et al. React: Synergizing reasoning and acting in language models[C]//International Conference on Learning Representations (ICLR). 2023.

[2] Wang L, Xu W, Lan Y, et al. Plan-and-solve prompting: Improving zero-shot chain-of-thought reasoning by large language models[J]. arXiv preprint arXiv:2305.04091, 2023.

[3] Shinn N, Cassano F, Gopinath A, et al. Reflexion: Language agents with verbal reinforcement learning[J]. Advances in Neural Information Processing Systems, 2023, 36: 8634-8652.

