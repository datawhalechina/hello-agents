<div align="right">
  English | <a href="./第六章%20框架开发实践.md">中文</a>
</div>

# Chapter 6 Framework Development Practice

In Chapter 4, we implemented the core workflows of several agents such as ReAct, Plan-and-Solve, and Reflection by writing native code. This process gave us an understanding of the internal execution logic of agents. Subsequently, in Chapter 5, we switched to the "user" perspective and experienced the convenience and efficiency brought by low-code platforms.

The goal of this chapter is to explore how to use some mainstream **agent frameworks** in the industry to efficiently and standardly build reliable agent applications. We will first overview the current mainstream agent frameworks on the market, and then experience the framework-driven development model through a complete practical case for several representative frameworks.

## 6.1 From Manual Implementation to Framework Development

Moving from writing one-time scripts to using a mature framework is an important mental leap in the field of software engineering. The code we wrote in Chapter 4 was primarily for teaching and understanding purposes. They can complete specific tasks well, but if we want to use them to build multiple, different types of agents with complex logic, we will soon encounter bottlenecks.

The essence of a framework is to provide a set of validated "specifications." It abstracts and encapsulates all the repetitive work common to all agents (such as main loops, state management, tool invocation, logging, etc.), allowing us to focus on their unique business logic when building new agents, rather than general underlying implementations.

### 6.1.1 Why Agent Frameworks Are Needed

Before we start the practical work, we first need to clarify why we should use frameworks. Compared to directly writing independent agent scripts, the value of using frameworks is mainly reflected in the following aspects:

1. **Improve Code Reuse and Development Efficiency**: This is the most direct value. A good framework will provide a general `Agent` base class or executor that encapsulates the core loop of agent operation (Agent Loop). Whether it's ReAct or Plan-and-Solve, they can be quickly built based on standard components provided by the framework, thus avoiding repetitive work.
2. **Achieve Decoupling and Extensibility of Core Components**: A robust agent system should consist of multiple loosely coupled modules. The framework's design will force us to separate different concerns:
   - **Model Layer**: Responsible for interacting with large language models, can easily replace different models (OpenAI, Anthropic, local models).
   - **Tool Layer**: Provides standardized tool definition, registration, and execution interfaces; adding new tools will not affect other code.
   - **Memory Layer**: Handles short-term and long-term memory, can switch different memory strategies according to needs (such as sliding window, summary memory). This modular design makes the entire system highly extensible, making it simple to replace or upgrade any component.
3. **Standardize Complex State Management**: The `Memory` class we implemented in `ReflectionAgent` is just a simple start. In real, long-running agent applications, state management is a huge challenge that needs to handle context window limitations, historical information persistence, multi-turn conversation state tracking, and other issues. A framework can provide a powerful and general state management mechanism, so developers don't have to deal with these complex issues every time.
4. **Simplify Observability and Debugging Process**: When agent behavior becomes complex, understanding its decision-making process becomes crucial. A well-designed framework can have built-in powerful observability capabilities. For example, by introducing an event callback mechanism (Callbacks), we can automatically trigger logging or data reporting at key nodes in the agent lifecycle (such as `on_llm_start`, `on_tool_end`, `on_agent_finish`), making it easy to track and debug the complete running trajectory of the agent. This is far more efficient and systematic than manually adding `print` statements in code.

Therefore, moving from manual implementation to framework development is not only a change in code organization, but also the necessary path to building complex, reliable, and maintainable agent applications.

### 6.1.2 Selection and Comparison of Mainstream Frameworks

The ecosystem of agent frameworks is developing at an unprecedented speed. If LangChain and LlamaIndex defined the paradigm of the first generation of general LLM application frameworks, then the new generation of frameworks is more focused on solving deep challenges in specific domains, especially **Multi-Agent Collaboration** and **Complex Workflow Control**.

In the subsequent practical work of this chapter, we will focus on four frameworks that are highly representative in these cutting-edge fields: AutoGen, AgentScope, CAMEL, and LangGraph. Their design philosophies are different, representing different technical paths for implementing complex agent systems, as shown in Figure 6.1.

<div align="center">
  <p>Table 6.1 Comparison of Four Agent Frameworks</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/01.png" alt="" width="90%"/>
</div>


- **AutoGen**: The core idea of AutoGen is to achieve collaboration through conversation<sup>[1]</sup>. It abstracts multi-agent systems as a group chat composed of multiple "conversable" agents. Developers can define different roles (such as `Coder`, `ProductManager`, `Tester`) and set interaction rules between them (for example, after `Coder` finishes writing code, `Tester` automatically takes over). The task-solving process is the process where these agents continuously converse, collaborate, and iterate in the group chat through automated message passing until the final goal is achieved.
- **AgentScope**: AgentScope is a fully functional development platform designed specifically for multi-agent applications<sup>[2]</sup>. Its core features are **ease of use** and **engineering**. It provides a very friendly programming interface that allows developers to easily define agents, build communication networks, and manage the entire application lifecycle. Its built-in **message passing mechanism** and support for distributed deployment make it very suitable for building and operating complex, large-scale multi-agent systems.
- **CAMEL**: CAMEL provides a novel collaboration method called **Role-Playing**<sup>[3]</sup>. Its core concept is that we only need to set the respective roles and common task goals for two agents (for example, `AI Researcher` and `Python Programmer`), and they can autonomously conduct multiple rounds of dialogue under the guidance of "**Inception Prompting**," inspiring and cooperating with each other to complete tasks together. It greatly reduces the complexity of designing multi-agent dialogue processes.
- **LangGraph**: As an extension of the LangChain ecosystem, LangGraph takes a different approach by modeling the agent's execution process as a **Graph**<sup>[4]</sup>. In traditional chain structures, information can only flow in one direction. LangGraph defines each operation (such as calling LLM, executing tools) as a **Node** in the graph and uses **Edges** to define the jump logic between nodes. This design naturally supports **Cycles**, making it exceptionally simple and intuitive to implement complex workflows such as Reflection that involve iteration, correction, and self-reflection.

In the following sections, we will deeply experience the framework-driven development model through a complete practical case for each of these four frameworks. **Please note** that all demonstrated project source files will be placed in the `code` folder, and only the principle part will be explained in the main text.

## 6.2 Framework One: AutoGen

As mentioned earlier, AutoGen's design philosophy is rooted in "driving collaboration through conversation." It cleverly maps complex task-solving processes to a series of automated conversations between agents with different roles. Based on this core concept, the AutoGen framework continues to evolve. We will use version `0.7.4` as an example because it is the latest version to date and represents an important architectural refactoring, transitioning from class inheritance design to a more flexible compositional architecture. To deeply understand and apply this framework, we first need to explain its most core constituent elements and underlying conversation interaction mechanisms.

### 6.2.1 Core Mechanisms of AutoGen

The release of version `0.7.4` is an important milestone in AutoGen's development, marking a fundamental innovation in the framework's underlying design. This update is not a simple addition of features but a rethinking of the overall architecture, aimed at improving the framework's modularity, concurrency performance, and developer experience.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/02.png" alt="" width="90%"/>
  <p>Figure 6.1 AutoGen Architecture Diagram</p>
</div>

(1) Evolution of Framework Structure

As shown in Figure 6.1, the most significant change in the new architecture is the introduction of clear layering and asynchronous-first design philosophy.

- **Layered Design:** The framework is split into two core modules:
  - `autogen-core`: As the underlying foundation of the framework, it encapsulates core functions such as interaction with language models and message passing. Its existence ensures the stability and future extensibility of the framework.
  - `autogen-agentchat`: Built on top of `core`, it provides high-level interfaces for developing conversational agent applications, simplifying the development process of multi-agent applications. This layering strategy makes each component's responsibilities clear and reduces system coupling.
- **Asynchronous First:** The new architecture fully transitions to asynchronous programming (`async/await`). In multi-agent collaboration scenarios, network requests (such as calling LLM APIs) are the main time-consuming operations. Asynchronous mode allows the system to handle other tasks while waiting for one agent's response, thus avoiding thread blocking and significantly improving concurrent processing capabilities and system resource utilization efficiency.

(2) Core Agent Components

Agents are the basic units for executing tasks. In version `0.7.4`, agent design is more focused and modular.

- **AssistantAgent (Assistant Agent):** This is the main task solver, whose core is encapsulating a large language model (LLM). Its responsibility is to generate logical and knowledgeable replies based on conversation history, such as proposing plans, writing articles, or writing code. Through different system messages (System Message), we can assign it different "expert" roles.
- **UserProxyAgent (User Proxy Agent):** This is a functionally unique component in AutoGen. It plays a dual role: it is both the "spokesperson" for human users, responsible for initiating tasks and conveying intentions; and a reliable "executor" that can be configured to execute code or call tools and feed results back to other agents. This design clearly distinguishes "thinking" (completed by `AssistantAgent`) from "action."

(3) From GroupChatManager to Team

When tasks require multiple agents to collaborate, a mechanism is needed to coordinate the conversation process. In earlier versions, `GroupChatManager` assumed this responsibility. In the new architecture, a more flexible `Team` or group chat concept is introduced, such as `RoundRobinGroupChat`.

- **Round Robin Group Chat (RoundRobinGroupChat):** This is a clear, sequential conversation coordination mechanism. It will have participating agents speak in turn according to a predefined order. This mode is very suitable for tasks with fixed processes, such as a typical software development process: the product manager first proposes requirements, then the engineer writes code, and finally the code reviewer checks.
- **Workflow:**
  1. First, create a `RoundRobinGroupChat` instance and add all agents participating in collaboration (such as product managers, engineers, etc.) to it.
  2. When a task starts, the group chat will activate the corresponding agents in turn according to the preset order.
  3. The selected agent responds based on the current conversation context.
  4. The group chat adds the new reply to the conversation history and activates the next agent.
  5. This process continues until the maximum number of conversation rounds is reached or preset termination conditions are met.

In this way, AutoGen simplifies complex collaborative relationships into an automated "round table meeting" with a clear process that is easy to manage. Developers only need to define the role and speaking order of each team member, and the rest of the collaboration process can be autonomously driven by the group chat mechanism.

In the next section, we will personally experience how to define agents with different roles in the new architecture and organize them in a group chat coordinated by `RoundRobinGroupChat` to collaboratively complete a real programming task by building an instance of a simulated software development team.

### 6.2.2 Software Development Team

After understanding AutoGen's core components and conversation mechanisms, this section will specifically demonstrate how to apply these new features through a complete practical case. We will build a simulated software development team composed of multiple agents with different professional skills, who will collaborate to complete a real software development task.

(1) Business Objective

Our goal is to develop a web application with a clear function: **display the current price of Bitcoin in real-time**. Although this task is small, it completely covers typical stages of software development: from requirement analysis, technology selection, coding implementation to code review and final testing. This makes it an ideal scenario for testing AutoGen's automated collaboration process.

(2) Agent Team Roles

To simulate a real software development process, we designed four agents with distinct responsibilities:

- **ProductManager (Product Manager):** Responsible for transforming users' vague requirements into clear, executable development plans.
- **Engineer:** Based on the development plan, responsible for writing specific application code.
- **CodeReviewer (Code Reviewer):** Responsible for reviewing code submitted by engineers to ensure its quality, readability, and robustness.
- **UserProxy (User Proxy):** Represents the end user, initiates the initial task, and is responsible for executing and verifying the final delivered code.

This role division is a key step in multi-agent system design, breaking down a complex task into multiple subtasks handled by domain "experts."

### 6.2.3 Core Code Implementation

Below, we will analyze the core code of this automated team step by step.

(1) Model Client Configuration

All LLM-based agents need a model client to interact with language models. AutoGen `0.7.4` provides a standardized `OpenAIChatCompletionClient` that can conveniently interface with any model service compatible with the OpenAI API specification (including OpenAI official service, Azure OpenAI, and local model services such as Ollama, etc.).

We create and configure the model client through an independent function and manage API Key and service address through environment variables. This is a good engineering practice that enhances code flexibility and security.

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

def create_openai_model_client():
    """Create and configure OpenAI model client"""
    return OpenAIChatCompletionClient(
        model=os.getenv("LLM_MODEL_ID", "gpt-4o"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    )
```

(2) Definition of Agent Roles

The core of defining agents lies in writing high-quality system messages (System Message). System messages are like setting "behavioral guidelines" and "professional knowledge bases" for agents, precisely specifying the agent's role, responsibilities, workflow, and even the way it interacts with other agents. A well-designed system message is key to ensuring that multi-agent systems can collaborate efficiently and accurately. In our software development team, we created an independent function for each role to encapsulate its definition.

**Product Manager (ProductManager)**

The product manager is responsible for initiating the entire process. Its system message not only defines its responsibilities but also standardizes the structure of its output and includes clear instructions to guide the conversation to the next stage (engineer).

```python
def create_product_manager(model_client):
    """Create product manager agent"""
    system_message = """You are an experienced product manager specializing in requirement analysis and project planning for software products.

Your core responsibilities include:
1. **Requirement Analysis**: Deeply understand user needs, identify core functions and boundary conditions
2. **Technical Planning**: Develop clear technical implementation paths based on requirements
3. **Risk Assessment**: Identify potential technical risks and user experience issues
4. **Coordination and Communication**: Communicate effectively with engineers and other team members

When receiving a development task, please analyze it according to the following structure:
1. Requirement understanding and analysis
2. Functional module division
3. Technology selection recommendations
4. Implementation priority sorting
5. Acceptance criteria definition

Please respond concisely and clearly, and say "Please engineer start implementation" after completing the analysis."""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
    )
```

**Engineer**

The engineer's system message focuses on technical implementation. It lists the engineer's technical expertise and specifies the specific action steps after receiving a task, also including instructions to guide the process to the code reviewer.

```python
def create_engineer(model_client):
    """Create software engineer agent"""
    system_message = """You are a senior software engineer skilled in Python development and web application construction.

Your technical expertise includes:
1. **Python Programming**: Proficient in Python syntax and best practices
2. **Web Development**: Expert in frameworks such as Streamlit, Flask, Django
3. **API Integration**: Rich experience in third-party API integration
4. **Error Handling**: Focus on code robustness and exception handling

When receiving a development task, please:
1. Carefully analyze technical requirements
2. Choose appropriate technical solutions
3. Write complete code implementation
4. Add necessary comments and explanations
5. Consider boundary cases and exception handling

Please provide complete runnable code and say "Please code reviewer check" after completion."""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,
    )
```

**Code Reviewer (CodeReviewer)**

The code reviewer's definition focuses on code quality, security, and standardization. Its system message details the review focus and process, ensuring a quality checkpoint before code delivery.

```python
def create_code_reviewer(model_client):
    """Create code reviewer agent"""
    system_message = """You are an experienced code review expert focusing on code quality and best practices.

Your review focus includes:
1. **Code Quality**: Check code readability, maintainability, and performance
2. **Security**: Identify potential security vulnerabilities and risk points
3. **Best Practices**: Ensure code follows industry standards and best practices
4. **Error Handling**: Verify the completeness and rationality of exception handling

Review process:
1. Carefully read and understand code logic
2. Check code standards and best practices
3. Identify potential issues and improvement points
4. Provide specific modification suggestions
5. Evaluate overall code quality

Please provide specific review comments and say "Code review completed, please user proxy test" after completion."""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,
    )
```

**User Proxy (UserProxy)**

`UserProxyAgent` is a special agent that does not rely on LLM for replies but acts as a user's proxy in the system. Its `description` field clearly describes its responsibilities. Especially important is that it is responsible for issuing the `TERMINATE` instruction after the task is finally completed to normally end the entire collaboration process.

```python
def create_user_proxy():
    """Create user proxy agent"""
    return UserProxyAgent(
        name="UserProxy",
        description="""User proxy, responsible for the following duties:
1. Propose development requirements on behalf of users
2. Execute final code implementation
3. Verify whether functions meet expectations
4. Provide user feedback and suggestions

Please reply TERMINATE after completing the test.""",
    )
```

Through these four independent definition functions, we not only built a fully functional "virtual team" but also demonstrated that "prompt engineering" through system messages is a core part of designing efficient multi-agent applications.

(3) Define Team Collaboration Process

In this case, the software development process is relatively fixed (requirements -> coding -> review -> testing), so `RoundRobinGroupChat` (round-robin group chat) is the ideal choice. We add the four agents to the participant list in business logic order.

```python
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# Define team chat and collaboration rules
team_chat = RoundRobinGroupChat(
    participants=[
        product_manager,
        engineer,
        code_reviewer,
        user_proxy
    ],
    termination_condition=TextMentionTermination("TERMINATE"),
    max_turns=20,
)
```

- **Participant Order:** The order of the `participants` list determines the order in which agents speak.
- **Termination Condition:** `termination_condition` is key to controlling when the collaboration process ends. Here we set that when any message contains the keyword "TERMINATE," the conversation ends. In our design, this instruction is issued by `UserProxy` after completing the final test.
- **Maximum Turns:** `max_turns` is a safety valve used to prevent conversations from falling into infinite loops and avoid unnecessary resource consumption.

(4) Startup and Execution

Since AutoGen `0.7.4` adopts an asynchronous architecture, the startup and execution of the entire collaboration process are completed in an asynchronous function and finally executed through `asyncio.run()`.

```python
async def run_software_development_team():
    # ... Initialize client and agents ...

    # Define task description
    task = """We need to develop a Bitcoin price display application with the following specific requirements:
            Core functions:
            - Display Bitcoin current price in real-time (USD)
            - Display 24-hour price change trend (percentage and amount of increase/decrease)
            - Provide price refresh function

            Technical requirements:
            - Use Streamlit framework to create web application
            - Simple and beautiful interface, user-friendly
            - Add appropriate error handling and loading status

            Please team collaborate to complete this task, from requirement analysis to final implementation."""

    # Asynchronously execute team collaboration and stream output conversation process
    result = await Console(team_chat.run_stream(task=task))
    return result

# Main program entry
if __name__ == "__main__":
    result = asyncio.run(run_software_development_team())
```

When the program runs, `task` is passed into `team_chat` as the initial message, the product manager receives the message as the first participant, and then the entire automated collaboration process begins.

(5) Expected Collaboration Effect

When we run this software development team, we can observe a complete collaboration process:

```bash
🔧 Initializing model client...
👥 Creating agent team...
🚀 Starting AutoGen software development team collaboration...
============================================================
---------- TextMessage (user) ----------
We need to develop a Bitcoin price display application with the following specific requirements:
...
Please team collaborate to complete this task, from requirement analysis to final implementation.
---------- TextMessage (ProductManager) ----------
### 1. Requirement Understanding and Analysis
...
Please engineer start implementation.
---------- TextMessage (Engineer) ----------
### Technical Solution Implementation
...
Please code reviewer check.
---------- TextMessage (CodeReviewer) ----------
### Code Review
...
Code review completed, please user proxy test.
---------- TextMessage (UserProxy) ----------
Requirements completed
---------- TextMessage (ProductManager) ----------
Great, thank you for your feedback! If you have any questions during use, or have other functional requirements and improvement suggestions, please feel free to let us know. We will continue to provide support and improvements. Looking forward to you having a pleasant experience with our application!
---------- TextMessage (Engineer) ----------
Glad to hear the project was completed successfully. If you or users have any questions or need help, please feel free to contact us. Thank you for your support of our work, let's work together to ensure the application runs stably and continuously optimize user experience!
---------- TextMessage (CodeReviewer) ----------
Thank you very much for everyone's efforts and collaboration, which enabled the project to be completed successfully. In the future, if there are more technical support needs or areas that need improvement, we are willing to contribute to the continuous optimization of the project. Looking forward to users enjoying a smooth experience, and also welcome more feedback and suggestions. Thank you again for the team's cooperation!
---------- TextMessage (UserProxy) ----------
Enter your response: TERMINATE
============================================================
✅ Team collaboration completed!

📋 Collaboration result summary:
- Number of participating agents: 4
- Task completion status: Success
```

The entire collaboration process demonstrates the advantages of the AutoGen framework: **natural conversation-driven collaboration**, **role specialization division**, **process automation management**, and **complete development closed loop**.

### 6.2.4 Analysis of AutoGen's Advantages and Limitations

Any technical framework has its specific applicable scenarios and design trade-offs. In this section, we will objectively analyze AutoGen's core advantages and the limitations and challenges it may face in practical applications.

(1) Advantages

- As shown in the case, we do not need to design complex state machines or control flow logic for the agent team, but naturally map a complete software development process to conversations between product managers, engineers, and reviewers. This approach is closer to the collaboration mode of human teams and significantly lowers the threshold for modeling complex tasks. Developers can focus more energy on defining "who (role)" and "what to do (responsibility)" rather than "how to do it (process control)."
- The framework allows assigning highly specialized roles to each agent through system messages (System Message). In the case, `ProductManager` focuses on requirements, while `CodeReviewer` focuses on quality. A well-designed agent can be reused in different projects, easy to maintain and extend.
- For process-oriented tasks, mechanisms like `RoundRobinGroupChat` provide clear, predictable collaboration processes. At the same time, the design of `UserProxyAgent` provides a natural interface for "Human-in-the-loop." It can serve as both the initiator of tasks and the supervisor and final acceptor of the process. This design ensures that automated systems are always under human supervision.

(2) Limitations

- Although `RoundRobinGroupChat` provides a sequential process, conversations based on LLM are inherently uncertain. Agents may produce replies that deviate from expectations, causing conversations to go in unexpected directions or even fall into loops.
- When the work results of the agent team do not meet expectations, the debugging process can be very tricky. Unlike traditional programs, we don't get a clear error stack but a long conversation history. This is called the "conversational debugging" dilemma.

(3) Configuration Supplement for Non-OpenAI Models

If you want to use non-OpenAI series models (such as DeepSeek, Tongyi Qianwen, etc.), in version 0.7.4, you need to pass a model information dictionary in the parameters of `OpenAIChatCompletionClient`. Taking DeepSeek as an example:

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    model_info={
        "function_calling": True,
        "max_tokens": 4096,
        "context_length": 32768,
        "vision": False,
        "json_output": True,
        "family": "deepseek",
        "structured_output": True,
    }
)
```

This `model_info` dictionary helps AutoGen understand the model's capability boundaries, thereby better adapting to different model services.



## 6.3 Framework Two: AgentScope

If AutoGen's design philosophy is "driving collaboration through conversation," then AgentScope represents another technical path: **engineering-first multi-agent platform**. AgentScope, developed by Alibaba DAMO Academy, is specifically designed for building large-scale, highly reliable multi-agent applications. It not only provides an intuitive and easy-to-use programming interface but, more importantly, has built-in enterprise-level features such as distributed deployment, fault recovery, and observability, making it particularly suitable for building production environment applications that need to run stably for a long time.

### 6.3.1 Design of AgentScope

Compared with AutoGen, the core difference of AgentScope lies in its **message-driven architectural design** and **industrial-grade engineering practices**. If AutoGen is more like a flexible "conversation studio," then AgentScope is a complete "agent operating system," providing developers with full lifecycle support from development, testing to deployment. Unlike the inheritance-based design adopted by many frameworks, AgentScope chooses **compositional architecture** and **message-driven mode**. This design not only enhances the modularity of the system but also lays the foundation for its excellent concurrency performance and distributed capabilities.

(1) Layered Architecture System

As shown in Figure 6.2, AgentScope adopts a clear layered modular design, forming a complete agent development ecosystem from bottom-level basic components to top-level application orchestration.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/03.png" alt="" width="90%"/>
  <p>Figure 6.2 AgentScope Architecture Diagram</p>
</div>

In this architecture, the bottom layer is the **Foundational Components** layer, which provides core building blocks for the entire framework. The `Message` component defines a unified message format, supporting everything from simple text interaction to complex multimodal content; the `Memory` component provides short-term and long-term memory management; the `Model API` layer abstracts calls to different large language models; and the `Tool` component encapsulates the agent's ability to interact with the external world.

Above the basic components, the **Agent-level Infrastructure** layer provides higher-level abstractions. This layer not only includes various pre-built agents (such as browser-using agents, deep research agents) but also implements the classic ReAct paradigm, supporting advanced features such as agent hooks, parallel tool calling, and state management. Particularly noteworthy is that this layer natively supports **asynchronous execution and real-time control**, which is an important advantage of AgentScope compared to other frameworks.

The **Multi-Agent Cooperation** layer is where AgentScope's core innovation lies. `MsgHub` serves as the message center, responsible for message routing and state management between agents; while the `Pipeline` system provides flexible workflow orchestration capabilities, supporting various execution modes such as sequential and concurrent. This design allows developers to easily build complex multi-agent collaboration scenarios.

The top **Deployment & Development** layer reflects AgentScope's emphasis on engineering. `AgentScope Runtime` provides a production-grade runtime environment, while `AgentScope Studio` provides developers with a complete visual development toolchain.

(2) Message-Driven

AgentScope's core innovation lies in its **message-driven architecture**. In this architecture, all agent interactions are abstracted as the sending and receiving of **messages**, rather than traditional function calls.

```python
from agentscope.message import Msg

# Standard structure of message
message = Msg(
    name="Alice",           # Sender name
    content="Hello, Bob!",  # Message content
    role="user",           # Role type
    metadata={             # Metadata information
        "timestamp": "2024-01-15T10:30:00Z",
        "message_type": "text",
        "priority": "normal"
    }
)
```

Using messages as the basic unit of interaction brings several key advantages:

- **Asynchronous Decoupling**: The sender and receiver of messages are decoupled in time, without needing to wait for each other, naturally supporting high-concurrency scenarios.
- **Location Transparency**: Agents do not need to care whether another agent is in a local process or on a remote server; the message system automatically handles routing.
- **Observability**: Every message can be logged, tracked, and analyzed, greatly simplifying debugging and monitoring of complex systems.
- **Reliability**: Messages can be persistently stored and retried. Even if the system fails, it can ensure the eventual consistency of interactions, improving the system's fault tolerance.

(3) Agent Lifecycle Management

In AgentScope, each agent has a clear lifecycle (initialization, running, pausing, destruction, etc.) and is implemented based on a unified base class `AgentBase`. Developers usually only need to focus on its core `reply` method.

```python
from agentscope.agents import AgentBase

class CustomAgent(AgentBase):
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        # Agent initialization logic

    def reply(self, x: Msg) -> Msg:
        # Agent's core response logic
        response = self.model(x.content)
        return Msg(name=self.name, content=response, role="assistant")

    def observe(self, x: Msg) -> None:
        # Agent's observation logic (optional)
        self.memory.add(x)
```

This design pattern separates the agent's internal logic from external communication. Developers only need to define how the agent "thinks and responds" in the `reply` method.

(4) Message Passing Mechanism

AgentScope has a built-in **Message Center (MsgHub)**, which is the hub of the entire message-driven architecture. MsgHub is not only responsible for message routing and distribution but also integrates advanced functions such as persistence and distributed communication. It has the following characteristics:

- **Flexible Message Routing**: Supports multiple communication modes such as point-to-point, broadcast, and multicast, and can build flexible and complex interaction networks.
- **Message Persistence**: Can automatically save all messages to databases (such as SQLite, MongoDB), ensuring that the state of long-running tasks can be recovered.
- **Native Distributed Support**: This is a signature feature of AgentScope. Agents can be deployed on different processes or servers, and `MsgHub` will automatically handle cross-node communication through RPC (Remote Procedure Call), completely transparent to developers.

These engineering capabilities provided by the underlying architecture make AgentScope more advantageous than traditional conversation-driven frameworks when handling complex application scenarios that require high concurrency and high reliability. Of course, this also requires developers to understand and adapt to the asynchronous programming paradigm of message-driven.

In the next section, we will deeply experience the capabilities of the AgentScope framework through a specific practical case, the Three Kingdoms Werewolf game, especially its advantages in handling concurrent interactions.

### 6.3.2 Three Kingdoms Werewolf Game

To deeply understand AgentScope's message-driven architecture and multi-agent collaboration capabilities, we will build a "Three Kingdoms Werewolf" game that integrates Chinese classical cultural elements. This case not only demonstrates AgentScope's advantages in handling complex multi-agent interactions but, more importantly, demonstrates how to fully leverage the power of message-driven architecture in a scenario that requires **real-time collaboration**, **role-playing**, and **strategic gaming**. Unlike traditional Werewolf, our "Three Kingdoms Werewolf" introduces classic characters such as Liu Bei, Guan Yu, and Zhuge Liang into the game. Each agent not only has to complete the basic tasks of Werewolf (such as werewolf killing, seer verification, villager reasoning) but also embodies the personality traits and behavior patterns of the corresponding Three Kingdoms characters. This design allows us to observe AgentScope's performance in handling **multi-level role modeling**.

(1) Architecture Design and Core Components

The system design of this case follows the principle of layered decoupling, dividing the game logic into three independent levels, each of which maps to one or more core components of AgentScope:

- **Game Control Layer**: A `ThreeKingdomsWerewolfGame` class serves as the main controller of the game, responsible for maintaining global state (such as player survival list, current game stage), advancing the game process (calling night phase, day phase), and judging victory or defeat.
- **Agent Interaction Layer**: Completely driven by `MsgHub`. All communication between agents, whether it's secret negotiations between werewolves or public debates during the day, is routed and distributed through the message center.
- **Role Modeling Layer**: Each player is an instance based on `DialogAgent`. Through carefully designed system prompts, we inject each agent with the dual identity of "game role" and "Three Kingdoms personality."

(2) Message-Driven Game Flow

The core design of this case is to use **message-driven** instead of **state machine** to manage the game flow. In traditional implementations, game phase transitions are usually controlled by a centralized state machine. In the AgentScope paradigm, the game flow is naturally modeled as a series of well-defined message interaction patterns.

For example, the implementation of the werewolf phase is not a simple function call but dynamically creates a temporary, private communication channel that only includes werewolf players through `MsgHub`:

```python
async def werewolf_phase(self, round_num: int):
    """Werewolf phase - demonstrating message-driven collaboration mode"""
    if not self.werewolves:
        return None

    # Establish werewolf-exclusive communication channel through message center
    async with MsgHub(
        self.werewolves,
        enable_auto_broadcast=True,
        announcement=await self.moderator.announce(
            f"Werewolves, please discuss tonight's kill target. Surviving players: {format_player_list(self.alive_players)}"
        ),
    ) as werewolves_hub:
        # Discussion phase: werewolves exchange strategies through messages
        for _ in range(MAX_DISCUSSION_ROUND):
            for wolf in self.werewolves:
                await wolf(structured_model=DiscussionModelCN)

        # Voting phase: collect and count werewolves' kill decisions
        werewolves_hub.set_auto_broadcast(False)
        kill_votes = await fanout_pipeline(
            self.werewolves,
            msg=await self.moderator.announce("Please choose kill target"),
            structured_model=WerewolfKillModelCN,
            enable_gather=False,
        )
```

The advantage of this design is that game logic is clearly expressed as "in a specific context, what mode of message exchange to conduct," rather than a series of rigid state transitions. Day discussion (full broadcast), seer verification (point-to-point request), and other phases all follow the same design paradigm.

(3) Constraining Game Rules with Structured Output

A key challenge in Werewolf games is how to ensure that agent behavior conforms to game rules. AgentScope's **structured output mechanism** provides a solution to this problem. We define strict data models for different game behaviors:

```python
class DiscussionModelCN(BaseModel):
    """Output format for discussion phase"""
    reach_agreement: bool = Field(
        description="Whether consensus has been reached",
        default=False
    )
    confidence_level: int = Field(
        description="Confidence level in current reasoning (1-10)",
        ge=1, le=10,
        default=5
    )
    key_evidence: Optional[str] = Field(
        description="Key evidence supporting your viewpoint",
        default=None
    )

class WitchActionModelCN(BaseModel):
    """Output format for witch action"""
    use_antidote: bool = Field(description="Whether to use antidote")
    use_poison: bool = Field(description="Whether to use poison")
    target_name: Optional[str] = Field(description="Poison target player name")
```

In this way, we not only ensure **format consistency** of agent output but, more importantly, achieve **automated constraint of game rules**. For example, the witch agent cannot use both antidote and poison on the same target at the same time, and the seer can only verify one player per night. These constraints are automatically executed through field definitions and validation logic of data models.

(4) Dual Challenge of Role Modeling

In this case, the most interesting technical challenge is how to make agents play two levels of roles well at the same time: **game functional role** (werewolf, seer, etc.) and **cultural personality role** (Liu Bei, Cao Cao, etc.). We solve this problem through prompt engineering:

```python
def get_role_prompt(role: str, character: str) -> str:
    """Get role prompt - integrating game rules and character personality"""
    base_prompt = f"""You are {character}, playing {role} in this Three Kingdoms Werewolf game.

Important rules:
1. You can only participate in the game through dialogue and reasoning
2. Do not attempt to call any external tools or functions
3. Strictly reply in the required JSON format

Role characteristics:
"""

    if role == "Werewolf":
        return base_prompt + f"""
- You are in the werewolf camp, with the goal of eliminating all good people
- At night, you can negotiate with other werewolves on kill targets
- During the day, you must hide your identity and mislead good people
- Speak and act with {character}'s personality
"""
```

This design allows us to observe an interesting phenomenon: different Three Kingdoms characters, when playing the same game role, will exhibit completely different strategies and speech styles. For example, "Cao Cao" playing a werewolf may appear more cunning and good at disguise, while "Zhang Fei" playing a werewolf may appear more direct and impulsive.

(5) Concurrent Processing and Fault Tolerance Mechanism

AgentScope's asynchronous architecture plays an important role in this multi-agent game. The game often has scenarios that require **simultaneously collecting decisions from multiple agents**, such as the voting phase:

```python
# Collect voting decisions from all players in parallel
vote_msgs = await fanout_pipeline(
    self.alive_players,
    await self.moderator.announce("Please vote to choose the player to eliminate"),
    structured_model=get_vote_model_cn(self.alive_players),
    enable_gather=False,
)
```

`fanout_pipeline` allows us to send the same message to all agents in parallel and asynchronously collect their responses. This not only improves the execution efficiency of the game but, more importantly, simulates the "simultaneous voting" scenario in real Werewolf games. At the same time, we add fault tolerance handling at key points:

```python
try:
    response = await wolf(
        "Please analyze the current situation and express your viewpoint.",
        structured_model=DiscussionModelCN
    )
except Exception as e:
    print(f"⚠️ {wolf.name} error during discussion: {e}")
    # Create default response to ensure game continues
    default_response = DiscussionModelCN(
        reach_agreement=False,
        confidence_level=5,
        key_evidence="Unable to analyze temporarily"
    )
```

This design ensures that even if an agent encounters an exception, the entire game process can continue.

(6) Case Output and Summary

To more intuitively experience AgentScope's operating mechanism, the following is a real running log excerpt from the game's night phase, showing the process of two werewolf agents playing "Sun Quan" and "Zhou Yu" conducting secret negotiations and executing a kill.

```
🎮 Welcome to Three Kingdoms Werewolf!

=== Game Initialization ===
Game Moderator: 📢 【Sun Quan】You are playing a werewolf in this Three Kingdoms Werewolf game, your character is Sun Quan. You can kill a player at night
Game Moderator: 📢 【Zhou Yu】You are playing a werewolf in this Three Kingdoms Werewolf game, your character is Zhou Yu. You can kill a player at night
...

Game Moderator: 📢 Three Kingdoms Werewolf game begins! Participants: Sun Quan, Zhou Yu, Cao Cao, Zhang Fei, Sima Yi, Zhao Yun
✅ Game setup complete, 6 players in total

=== Round 1 ===
🌙 Night 1 falls, everyone close your eyes...

【Werewolf Phase】
Game Moderator: 📢 🐺 Werewolves please open your eyes, choose tonight's kill target...
Game Moderator: 📢 Werewolves, please discuss tonight's kill target. Surviving players: Sun Quan, Zhou Yu, Cao Cao, Zhang Fei, Sima Yi, Zhao Yun

Sun Quan: Tonight we should eliminate Zhou Yu, this person is extremely intelligent and poses a great threat to us.
Zhou Yu: Sun Quan, you make a good point. But although Zhou Yu is intelligent, he may not be the biggest threat tonight. Cao Cao has great power, if we don't eliminate him early, it may be unfavorable to us.
Sun Quan: Cao Cao is indeed a threat, but if Zhou Yu lives, he can see through our schemes. Better to solve the immediate hidden danger first.
Zhou Yu: Sun Quan, your concern is not without reason. But if Cao Cao becomes our enemy, he can unite other forces to pose a greater threat to us.
Sun Quan: What you say also makes sense, Cao Cao's alliance is indeed troublesome. Then let's deal with Cao Cao first.
Zhou Yu: Very good, Sun Quan. Cao Cao is our primary target tonight.

Game Moderator: 📢 Please choose kill target
Sun Quan: I agree, Cao Cao must be eliminated.
Zhou Yu: I agree, Cao Cao is the target we need to solve tonight.

【Seer Phase】
Game Moderator: 📢 🔮 Seer please open your eyes, choose the player to verify...
Cao Cao: I want to verify Sun Quan.
Game Moderator: 📢 Verification result: Sun Quan is a werewolf

【Witch Phase】
Game Moderator: 📢 🧙‍♀️ Witch please open your eyes...
Game Moderator: 📢 Tonight Cao Cao was killed by werewolves
Zhang Fei: I used the antidote to save Cao Cao last night, now the antidote has been used up.
Game Moderator: 📢 You used the antidote to save Cao Cao

Game Moderator: 📢 Last night was peaceful, no one died.

【Day Discussion Phase】
Game Moderator: 📢 ☀️ Day 1 dawns, everyone please open your eyes...
Game Moderator: 📢 Now begin free discussion. Surviving players: Sun Quan, Zhou Yu, Cao Cao, Zhang Fei, Sima Yi, Zhao Yun

Sun Quan: Everyone, Cao Cao has great power and is a potential threat to us all. Tonight I suggest we concentrate our forces against him.
Zhou Yu: Sun Quan is absolutely right, Cao Cao is not only powerful himself but may also ally with other players, posing a greater threat to us.
Cao Cao: I verified Sun Quan last night, originally thought he was a good person, but the game moderator's result was werewolf. This means there's a werewolf lying.
Zhang Fei: I did save Cao Cao last night, indicating he was attacked by werewolves. But Cao Cao's verification result of Sun Quan is suspicious.
Sima Yi: There seems to be a contradiction between Cao Cao's verification result and Zhang Fei's saving action, we need more information to determine who is the werewolf.
Zhao Yun: The situation is indeed complex, we need to carefully analyze everyone's statements.

【Voting Phase】
Game Moderator: 📢 Please vote to choose the player to eliminate

Sun Quan: Cao Cao's threat is still great, I insist we should vote for him.
Zhou Yu: Based on last night's situation, I think we should vote for Cao Cao first, his threat is the greatest.
Cao Cao: I choose to vote for Sun Quan. According to the game moderator's feedback, Sun Quan is indeed a werewolf.
Zhang Fei: I insist on the fact that I saved Cao Cao last night, but the fact that Sun Quan was found to be a werewolf confuses me.
Sima Yi: We need more information to determine who is the werewolf.

[Game continues...]
```

### 6.3.3 Analysis of AgentScope's Advantages and Limitations

Through this "Three Kingdoms Werewolf" case, we deeply experienced the core advantages of the AgentScope framework. The framework, with its message-driven architecture as the core, elegantly maps complex game processes into a series of concurrent, asynchronous message passing events, thereby avoiding the rigidity and complexity of traditional state machines. Combined with its powerful structured output capability, we directly transform game rules into code-level constraints, greatly improving system stability and predictability. This design paradigm not only demonstrates its native concurrency advantages in performance but also ensures that even if a single agent encounters an exception, the overall process can run robustly in fault tolerance handling.

However, AgentScope's engineering advantages also bring a certain complexity cost. Although its message-driven architecture is powerful, it has high technical requirements for developers, requiring understanding of asynchronous programming, distributed communication, and other concepts. For simple multi-agent conversation scenarios, this architecture may seem overly complex, with the risk of "over-engineering." In addition, as a relatively new framework, its ecosystem and community resources still need further improvement. Therefore, AgentScope is more suitable for building large-scale, highly reliable production-level multi-agent systems, while for rapid prototype development or simple application scenarios, choosing a more lightweight framework may be more appropriate.



## 6.4 Framework Three: CAMEL

Unlike comprehensive frameworks like AutoGen and AgentScope, CAMEL's original core goal is to explore how to enable two agents to autonomously collaborate to solve complex tasks through "role-playing" with minimal human intervention.

### 6.4.1 Autonomous Collaboration in CAMEL

The cornerstone of CAMEL's autonomous collaboration is two core concepts: **Role-Playing** and **Inception Prompting**.

(1) Role-Playing

In CAMEL's original design, a task is usually completed by two agents collaborating. These two agents are assigned complementary, clearly defined "roles." One plays the **"AI User"**, responsible for proposing requirements, issuing instructions, and conceiving task steps; the other plays the **"AI Assistant"**, responsible for executing specific operations and providing solutions based on instructions.

For example, in a task to "develop a stock trading strategy analysis tool":

- The **AI User** role might be a "senior stock trader." It understands the market and strategies but doesn't understand programming.
- The **AI Assistant** role is an "excellent Python programmer." It is proficient in programming but knows nothing about stock trading.

Through this setup, the task-solving process is naturally transformed into a conversation between two "cross-domain experts." The trader proposes professional requirements, the programmer transforms them into code implementation, and the two collaborate to complete complex tasks that neither could accomplish independently.

(2) Inception Prompting

Simply setting roles is not enough. How can we ensure that two AIs can always "stay in their roles" and efficiently move toward a common goal without continuous human supervision? This is where CAMEL's core technology, inception prompting, comes into play. "Inception prompting" is a carefully designed, structured initial instruction (System Prompt) injected into both agents before the conversation begins. This instruction is like an "action program" implanted in the agents, and it usually includes the following key parts:

- **Clarify own role**: For example, "You are a senior stock trader..."
- **Inform collaborator's role**: For example, "You are working with an excellent Python programmer..."
- **Define common goal**: For example, "Your common goal is to develop a stock trading strategy analysis tool."
- **Set behavioral constraints and communication protocols**: This is the most critical part. For example, the instruction will require the AI user to "propose only one clear, specific step at a time" and require the AI assistant to "not ask for more details before completing the previous step," while also specifying that both parties need to use specific markers (such as `<SOLUTION>`) at the end of their replies to identify task completion.

These constraints ensure that the conversation does not deviate from the topic or fall into ineffective loops but advances in a highly structured, task-driven manner, as shown in Figure 6.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/04.png" alt="" width="90%"/>
  <p>Figure 6.3 CAMEL Creating Stock Trading Robot</p>
</div>

In the next section, we will experience this process through a specific example.

### 6.4.2 AI Popular Science E-book

To understand CAMEL framework's role-playing capabilities, we will build a practical collaborative case: having an AI psychologist work with an AI author to co-create a short e-book on "The Psychology of Procrastination." This case embodies CAMEL's core advantage of allowing two agents to leverage their respective professional domains to collaboratively complete complex creative tasks that a single agent would struggle with.

(1) Task Setup

**Scenario Setup**: Create a popular science e-book on the psychology of procrastination for general readers, requiring both scientific rigor and good readability.

**Agent Roles**:

- **Psychologist**: Possesses deep theoretical foundation in psychology, familiar with cognitive behavioral science, neuroscience, and other related fields, able to provide professional academic insights and empirical research support
- **Writer**: Has excellent writing skills and narrative ability, good at transforming complex academic concepts into vivid and easy-to-understand text, focusing on reader experience and content readability

(2) Define Collaboration Task

First, we need to clarify the common goal of the two AI experts. We define this task through a detailed string `task_prompt`.

```python
from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated

# Define collaboration task
task_prompt = """
Create a short e-book on "The Psychology of Procrastination" for general readers interested in psychology.
Requirements:
1. Content should be scientifically rigorous, based on empirical research
2. Language should be easy to understand, avoiding excessive professional terminology
3. Include practical improvement suggestions and case analysis
4. Length controlled at 8000-10000 words
5. Clear structure, including introduction, core chapters, and summary
"""

print(Fore.YELLOW + f"Collaboration task:\n{task_prompt}\n")
```

`task_prompt` is the "task specification" for the entire collaboration. It is not only the goal we want to achieve but will also be used behind the scenes by CAMEL to generate "inception prompts," ensuring that the conversation between the two agents always revolves around this core goal.

(3) Initialize Role-Playing "Society"

Next, we create a `RolePlaying` session instance. This is CAMEL's core operation, which quickly builds a two-agent collaboration "society" based on the roles and tasks we provide.

```python
# Initialize role-playing session
# AI writer as "user", responsible for proposing writing structure and requirements
# AI psychologist as "assistant", responsible for providing professional knowledge and content
role_play_session = RolePlaying(
    assistant_role_name="Psychologist",
    user_role_name="Writer",
    task_prompt=task_prompt,
    with_task_specify=False, # In this example, we directly use the given task_prompt
)

print(Fore.CYAN + f"Specific task description:\n{role_play_session.task_prompt}\n")
```

`RolePlaying` is a high-level API provided by CAMEL that encapsulates complex prompt engineering. We only need to pass in the names of the two roles and the task. In CAMEL's design, the `user` role is the "driver" and "demander" of the conversation, while the `assistant` role is the "executor" and "solution provider." Therefore, we assign the "writer" responsible for planning structure to `user_role_name` and the "psychologist" responsible for providing professional knowledge to `assistant_role_name`.

(4) Start and Run Automated Conversation

Finally, we write a loop to drive the entire conversation process, allowing the two AI experts to begin their automated collaboration.

```python
# Start collaboration conversation
chat_turn_limit, n = 30, 0
# Call init_chat() to get the initial conversation message generated by AI
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n += 1
    # step() method drives a complete round of conversation, AI user and AI assistant each speak once
    assistant_response, user_response = role_play_session.step(input_msg)

    # Check if messages are returned to prevent premature conversation termination
    if assistant_response.msg is None or user_response.msg is None:
        break

    print_text_animated(Fore.BLUE + f"Writer (AI User):\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"Psychologist (AI Assistant):\n\n{assistant_response.msg.content}\n")

    # Check task completion flag
    if "<CAMEL_TASK_DONE>" in user_response.msg.content or "<CAMEL_TASK_DONE>" in assistant_response.msg.content:
        print(Fore.MAGENTA + "✅ E-book creation completed!")
        break

    # Use assistant's reply as input for next round of conversation
    input_msg = assistant_response.msg

print(Fore.YELLOW + f"Total of {n} rounds of collaborative conversation")
```

This `while` loop is the core of automated collaboration. The conversation is automatically initiated by the `init_chat()` method based on the task and roles, without the need to manually write an opening. Each step of the loop drives a complete round of interaction by calling `step()` (writer proposes requirements, psychologist provides content), and uses the psychologist's output from the previous round as input for the next round, forming a chain of creation. The entire process will continue until the preset conversation turn limit is reached, or automatically terminates after either agent outputs the task completion flag `<CAMEL_TASK_DONE>`.

(5) Collaboration Process Demonstration

When executing the above code, we don't just get a long string of monotonous Q&A but can observe a highly structured collaboration process, like a human expert team, automatically proceeding. The entire creation process naturally divides into several stages:

**Stage 1 (approximately rounds 1-5): Framework Building and Goal Alignment** In the early stages of the conversation, the "writer" agent first plays the leading role, proposing initial ideas for the overall structure and chapter arrangement of the e-book. Subsequently, the "psychologist" reviews and supplements this framework from a professional perspective, ensuring that core academic modules (such as theoretical foundations, key concepts, etc.) are not omitted, thereby reaching consensus on the final output at the beginning of collaboration.

**Stage 2 (approximately rounds 6-20): Core Content Generation and Knowledge Translation** This is the most efficient content creation stage. The collaboration mode becomes a stable "request-response" loop:

- **Psychologist**: Responsible for providing "hardcore" professional knowledge, such as scientific explanations of core concepts like "temporal discounting theory" and "executive function deficits," and citing relevant experimental research to support viewpoints.
- **Writer**: Plays the role of "translator," transforming these rigorous but potentially obscure academic concepts into vivid, figurative metaphors and life-related cases. For example, it might compare the concept of "present bias in the brain" to "a willful child who only cares about immediate candy and not long-term health."

**Stage 3 (approximately rounds 21-25): Iterative Optimization and Quality Assurance** When the main content of the book is completed, the focus of the conversation shifts to polishing and improving the existing text. At this time, the roles of the two agents undergo subtle changes:

- **Writer**: More focused on examining the overall fluency, logical coherence, and language style of the article, proposing revision suggestions from the perspective of "reader experience."
- **Psychologist**: Again plays the role of "fact checker," ensuring that the scientific accuracy of core knowledge is not lost during translation and polishing, and supplementing certain viewpoints with more powerful empirical research support.

**Stage 4 (Conclusion): Summary and Elevation** In the last few rounds of conversation, both parties collaborate to complete the summary of practical suggestions and the review of the entire book, ensuring that the e-book has a clear, powerful ending that leaves a deep impression on readers and provides practical value.

```
Collaboration task:
Create a short e-book on "The Psychology of Procrastination" for general readers interested in psychology.
Requirements:
1. Content should be scientifically rigorous, based on empirical research
2. Language should be easy to understand, avoiding excessive professional terminology
3. Include practical improvement suggestions and case analysis
4. Length controlled at 8000-10000 words
5. Clear structure, including introduction, core chapters, and summary

Specific task description:
Write an 8000–10000 word short e-book "The Psychology of Procrastination" for general readers: empirically based, easy to understand. Structure: introduction, causes (cognitive/emotional/reward), motivation and decision-making, habit formation and intervention, practical strategies and exercises, three case analyses, summary and resources. Each chapter contains research citations and actionable steps.

Writer:
Instruction: Please write a 400–600 word Chinese draft for the "Introduction" chapter of the e-book...
Input: None

Psychologist:
Solution:
Draft: Procrastination refers to the behavior and internal tendency of repeatedly postponing or avoiding a task despite knowing it should be completed. It can be an occasional time management problem...

Next request.

Writer:
Instruction: Please revise the following introduction draft into a 450–550 word Chinese text...
Input: Draft: Procrastination refers to the behavior and internal tendency of repeatedly postponing or avoiding a task...
.....
```

### 6.4.3 Analysis of CAMEL's Advantages and Limitations

Through the previous e-book creation case, we deeply experienced CAMEL framework's unique role-playing paradigm. Now let's objectively analyze the advantages and limitations of this design philosophy to make wise technical choices in actual projects.

(1) Advantages

CAMEL's greatest advantage lies in its "light architecture, heavy prompting" design philosophy. Compared to AutoGen's complex conversation management and AgentScope's distributed architecture, CAMEL can achieve high-quality agent collaboration through carefully designed initial prompts. This naturally emergent collaborative behavior is often more flexible and efficient than hard-coded workflows.

It's worth noting that the CAMEL framework is undergoing rapid development and evolution. From its [GitHub repository](https://github.com/camel-ai/camel), we can see that CAMEL is far more than a simple two-agent collaboration framework and currently has:

- **Multimodal Capabilities**: Supports agent collaboration in multiple modalities such as text, image, and audio
- **Tool Integration**: Built-in rich tool library, including search, calculation, code execution, etc.
- **Model Adaptation**: Supports multiple LLM backends such as OpenAI, Anthropic, Google, and open-source models
- **Ecosystem Linkage**: Achieved interoperability with mainstream frameworks such as LangChain, CrewAI, and AutoGen

(2) Main Limitations

1. High Dependence on Prompt Engineering

CAMEL's success largely depends on the quality of initial prompts. This brings several challenges:

- **Prompt Design Threshold**: Requires deep understanding of the target domain and LLM behavioral characteristics
- **Debugging Complexity**: When collaboration is ineffective, it's difficult to pinpoint whether the problem lies in role definition, task description, or interaction rules
- **Consistency Challenge**: Different LLMs may have different understandings of the same prompt

2. Collaboration Scale Limitations

Although CAMEL performs excellently in two-agent collaboration, it faces challenges when handling large-scale multi-agent scenarios:

- **Conversation Management**: Lacks complex conversation routing mechanisms like AutoGen
- **State Synchronization**: Doesn't have distributed state management capabilities like AgentScope
- **Conflict Resolution**: Lacks effective arbitration mechanisms when multiple agents disagree

3. Task Applicability Boundaries

CAMEL is particularly suitable for tasks requiring deep collaboration and creative thinking, but may not be the optimal choice in certain scenarios:

- **Strict Process Control**: For tasks requiring precise step control, LangGraph's graph structure is more suitable
- **Large-scale Concurrency**: AgentScope's message-driven architecture has more advantages in high-concurrency scenarios
- **Complex Decision Trees**: AutoGen's group chat mode is more flexible in multi-party decision scenarios

Overall, CAMEL represents a unique and elegant multi-agent collaboration paradigm. Through its "human-centered" role-playing design, it transforms complex system engineering problems into intuitive interpersonal collaboration patterns. As its ecosystem continues to improve and functions continue to expand, CAMEL is becoming one of the important choices for building intelligent collaboration systems.

## 6.5 Framework Four: LangGraph

### 6.5.1 LangGraph Structure Overview

LangGraph, as an important extension of the LangChain ecosystem, represents a completely new direction in agent framework design. Unlike the "conversation"-based frameworks introduced earlier (such as AutoGen and CAMEL), LangGraph models the agent's execution flow as a **State Machine** and represents it as a **Directed Graph**. In this paradigm, the graph's **Nodes** represent specific computational steps (such as calling LLM, executing tools), while **Edges** define the transition logic from one node to another. The revolutionary aspect of this design is that it natively supports loops, making it unprecedentedly intuitive and simple to build complex agent workflows capable of iteration, reflection, and self-correction.

To understand LangGraph, we need to first grasp its three basic components.

**First, is the global state (State)**. The entire graph's execution process revolves around a shared state object. This state is usually defined as a Python `TypedDict`, which can contain any information you need to track, such as conversation history, intermediate results, iteration count, etc. All nodes can read and update this central state.

```python
from typing import TypedDict, List

# Define global state data structure
class AgentState(TypedDict):
    messages: List[str]      # Conversation history
    current_task: str        # Current task
    final_answer: str        # Final answer
    # ... any other state to track
```

**Second, are the nodes (Nodes)**. Each node is a Python function that receives the current state as input and returns an updated state as output. Nodes are units that perform specific work.

```python
# Define a "planner" node function
def planner_node(state: AgentState) -> AgentState:
    """Formulate a plan based on current task and update state."""
    current_task = state["current_task"]
    # ... call LLM to generate plan ...
    plan = f"Plan generated for task '{current_task}'..."

    # Append new message to state
    state["messages"].append(plan)
    return state

# Define an "executor" node function
def executor_node(state: AgentState) -> AgentState:
    """Execute latest plan and update state."""
    latest_plan = state["messages"][-1]
    # ... execute plan and get result ...
    result = f"Result of executing plan '{latest_plan}'..."

    state["messages"].append(result)
    return state
```

**Finally, are the edges (Edges)**. Edges are responsible for connecting nodes and defining the direction of the workflow. The simplest edge is a regular edge, which specifies that the output of one node always flows to another fixed node. LangGraph's most powerful feature lies in **Conditional Edges**. It uses a function to judge the current state and then dynamically decides which node to jump to next. This is the key to implementing loops and complex logical branches.

```python
def should_continue(state: AgentState) -> str:
    """Condition function: decide next route based on state."""
    # Assume if messages are less than 3, need to continue planning
    if len(state["messages"]) < 3:
        # Returned string needs to match the key defined when adding conditional edge
        return "continue_to_planner"
    else:
        state["final_answer"] = state["messages"][-1]
        return "end_workflow"
```

After defining state, nodes, and edges, we can assemble them into an executable workflow like building blocks.

```python
from langgraph.graph import StateGraph, END

# Initialize a state graph and bind our defined state structure
workflow = StateGraph(AgentState)

# Add node functions to the graph
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)

# Set graph entry point
workflow.set_entry_point("planner")

# Add regular edge, connecting planner and executor
workflow.add_edge("planner", "executor")

# Add conditional edge, implementing dynamic routing
workflow.add_conditional_edges(
    # Starting node
    "executor",
    # Judgment function
    should_continue,
    # Route mapping: map judgment function's return value to target node
    {
        "continue_to_planner": "planner", # If returns "continue_to_planner", jump back to planner node
        "end_workflow": END               # If returns "end_workflow", end process
    }
)

# Compile graph, generate executable application
app = workflow.compile()

# Run graph
inputs = {"current_task": "Analyze recent AI industry news", "messages": []}
for event in app.stream(inputs):
    print(event)
```

### 6.5.2 Three-Step Q&A Assistant
After understanding LangGraph's core concepts, we will consolidate what we've learned through a practical case. We will build a simplified Q&A dialogue assistant that follows a clear, fixed three-step process to answer user questions:

1. **Understand**: First, analyze the user's query intent.
2. **Search**: Then, simulate searching for information related to the intent.
3. **Answer**: Finally, generate the final answer based on the intent and searched information.

This case will clearly demonstrate how to define state, create nodes, and linearly connect them into a complete workflow. We will break down the code into four core steps: define state, create nodes, build graph, and run application.

(1) Define Global State

First, we need to define a global state that runs through the entire workflow. **This is a shared data structure that is passed between each node of the graph, serving as the persistent context of the workflow.** Each node can read data from this structure and update it.

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class SearchState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str      # User requirement summary after LLM understanding
    search_query: str    # Optimized search query for Tavily API
    search_results: str  # Results returned by Tavily search
    final_answer: str    # Final generated answer
    step: str            # Mark current step
```

We created the `SearchState` `TypedDict`, defining a clear data schema for the state object. A key design is the inclusion of both `user_query` and `search_query` fields. This allows the agent to first optimize the user's natural language question into refined keywords more suitable for search engines, thereby significantly improving the quality of search results.

(2) Define Workflow Nodes

After defining the state structure, the next step is to create the various nodes that make up our workflow. In LangGraph, each node is a Python function that performs a specific task. These functions receive the current state object as input and return a dictionary containing updated fields.

Before defining nodes, we first complete the project initialization setup, including loading environment variables and instantiating the large language model.

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tavily import TavilyClient

# Load environment variables from .env file
load_dotenv()

# Initialize model
# We will use this llm instance to drive the intelligence of all nodes
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID", "gpt-4o-mini"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    temperature=0.7
)
# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
```

Now, let's create the three core nodes one by one.

(1) Understand and Query Node

This node is the first step of the workflow. Its responsibility is to understand user intent and generate an optimized search query for it.

```python
def understand_query_node(state: SearchState) -> dict:
    """Step 1: Understand user query and generate search keywords"""
    user_message = state["messages"][-1].content

    understand_prompt = f"""Analyze the user's query: "{user_message}"
Please complete two tasks:
1. Concisely summarize what the user wants to know
2. Generate keywords most suitable for search engines (Chinese or English, must be precise)

Format:
Understanding: [User requirement summary]
Search terms: [Best search keywords]"""

    response = llm.invoke([SystemMessage(content=understand_prompt)])
    response_text = response.content

    # Parse LLM's output, extract search keywords
    search_query = user_message # Default to using original query
    if "Search terms:" in response_text or "搜索词：" in response_text:
        if "Search terms:" in response_text:
            search_query = response_text.split("Search terms:")[1].strip()
        else:
            search_query = response_text.split("搜索词：")[1].strip()

    return {
        "user_query": response_text,
        "search_query": search_query,
        "step": "understood",
        "messages": [AIMessage(content=f"I will search for you: {search_query}")]
    }
```

This node uses a structured prompt to require the LLM to simultaneously complete two tasks: "intent understanding" and "keyword generation," and updates the parsed dedicated search keywords to the state's `search_query` field, preparing for the next step of precise search.

(2) Search Node

This node is responsible for executing the agent's "tool usage" capability. It will call the Tavily API for real internet search and has basic error handling functionality.

```python
def tavily_search_node(state: SearchState) -> dict:
    """Step 2: Use Tavily API for real search"""
    search_query = state["search_query"]
    try:
        print(f"🔍 Searching: {search_query}")
        response = tavily_client.search(
            query=search_query, search_depth="basic", max_results=5, include_answer=True
        )
        # ... (process and format search results) ...
        search_results = ... # Formatted result string

        return {
            "search_results": search_results,
            "step": "searched",
            "messages": [AIMessage(content="✅ Search completed! Organizing answer...")]
        }
    except Exception as e:
        # ... (handle error) ...
        return {
            "search_results": f"Search failed: {e}",
            "step": "search_failed",
            "messages": [AIMessage(content="❌ Search encountered a problem...")]
        }
```

This node initiates a real API call through `tavily_client.search`. It is wrapped in a `try...except` block to catch possible exceptions. If the search fails, it updates the `step` state to `"search_failed"`, which will be used by the next node to trigger a fallback plan.

(3) Answer Node

The final answer node can choose different answering strategies based on whether the previous search was successful, possessing a certain degree of flexibility.

```python
def generate_answer_node(state: SearchState) -> dict:
    """Step 3: Generate final answer based on search results"""
    if state["step"] == "search_failed":
        # If search failed, execute fallback strategy, answer based on LLM's own knowledge
        fallback_prompt = f"Search API is temporarily unavailable, please answer the user's question based on your knowledge:\nUser question: {state['user_query']}"
        response = llm.invoke([SystemMessage(content=fallback_prompt)])
    else:
        # Search successful, generate answer based on search results
        answer_prompt = f"""Provide a complete and accurate answer to the user based on the following search results:
User question: {state['user_query']}
Search results:\n{state['search_results']}
Please synthesize the search results and provide an accurate, useful answer..."""
        response = llm.invoke([SystemMessage(content=answer_prompt)])

    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }
```

This node executes conditional logic by checking the value of `state["step"]`. If the search fails, it will use the LLM's internal knowledge to answer and inform the user of the situation. If the search succeeds, it will use a prompt containing real-time search results to generate a timely and evidence-based answer.

(4) Build Graph

We connect all nodes together.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

def create_search_assistant():
    workflow = StateGraph(SearchState)

    # Add nodes
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("answer", generate_answer_node)

    # Set linear process
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    # Compile graph
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app
```

(5) Running Case Demonstration

After running this script, you can ask some questions that require real-time information, such as the case in our first chapter: `I'm going to Beijing tomorrow, what's the weather like? Are there suitable attractions?`

You will see the terminal clearly display the agent's "thinking" process:

```
🔍 Intelligent Search Assistant Started!
I will use Tavily API to search for the latest and most accurate information for you
Supports various questions: news, technology, knowledge Q&A, etc.
(Enter 'quit' to exit)

🤔 What would you like to know: I'm going to Beijing tomorrow, what's the weather like? Are there suitable attractions?

============================================================
🧠 Understanding phase: I understand your needs: Understanding: The user wants to know about tomorrow's weather in Beijing and suitable attraction recommendations.
Search terms: Beijing tomorrow weather attraction recommendations Beijing weather tomorrow attractions
🔍 Searching: Beijing tomorrow weather attraction recommendations Beijing weather tomorrow attractions
🔍 Search phase: ✅ Search completed! Found relevant information, organizing answer for you...

💡 Final Answer:
Tomorrow (September 17, 2025) Beijing's weather forecast shows it is expected to be cloudy, with temperatures ranging from 17°C (62°F) to 25°C (77°F). This mild weather is very suitable for outdoor activities.

### Suitable Attraction Recommendations:
1. **Great Wall**: As one of China's most famous historical sites, the Great Wall is a must-visit. You can choose popular sections like Badaling or Mutianyu for your tour.

2. **Forbidden City**: The Forbidden City was the imperial palace of the Ming and Qing dynasties, with rich history and culture, suitable for tourists interested in Chinese history.

3. **Tiananmen Square**: This is one of China's symbols, with many important buildings and monuments on the square, suitable for taking photos.

4. **Summer Palace**: A very beautiful royal garden, suitable for strolling and enjoying natural scenery, especially the lakes and ancient buildings.

5. **798 Art District**: If you're interested in modern art, the 798 Art District is a place that integrates art, culture, and creativity, suitable for exploration and photography.

### Tips:
- Since tomorrow's weather is good, it's recommended to plan your travel route in advance and prepare some water and snacks to maintain sufficient energy during the tour.
- Since weather changes may affect the tour experience, it's recommended to check real-time weather updates.

Hope this information helps you arrange a pleasant Beijing trip! If you need more information about attractions or travel advice, feel free to ask anytime.

============================================================

🤔 What would you like to know:
```

And it is a continuously interactive assistant, you can continue to ask questions.

### 6.5.3 Analysis of LangGraph's Advantages and Limitations

Any technical framework has its specific applicable scenarios and design trade-offs. In this section, we will objectively analyze LangGraph's core advantages and the limitations it may face in practical applications.

(1) Advantages

- As shown in our intelligent search assistant case, LangGraph explicitly defines a complete real-time Q&A process as a "flowchart" composed of states, nodes, and edges. The greatest advantage of this design is **high controllability and predictability**. Developers can precisely plan every step of the agent's behavior, which is crucial for building production-level applications that require high reliability and auditability. Its most powerful feature lies in **native support for cycles**. Through conditional edges, we can easily build "reflection-correction" loops. For example, in our case, if the search fails, we can design a path to fall back to a backup plan. This is key to building agents capable of self-optimization and fault tolerance.

- In addition, since each node is an independent Python function, this brings **high modularity**. At the same time, inserting a node waiting for human review in the process becomes very straightforward, providing a solid foundation for implementing reliable "Human-in-the-loop" collaboration.

(2) Limitations

- Compared to conversation-based frameworks, LangGraph requires developers to write more **boilerplate code**. Defining states, nodes, edges, and a series of operations makes the development process more cumbersome for simple tasks. Developers need to think more about "how to control the process (how)" rather than just "what to do (what)". Since the workflow is predefined, LangGraph's behavior is controllable but also lacks the dynamic, **"emergent" interaction** of conversational agents. Its strength lies in executing a determined, reliable process, rather than simulating open-ended, unpredictable social collaboration.

- The debugging process also presents challenges. Although the process is clearer than conversation history, problems may occur at multiple points: logical errors within a node, mutations in state data passed between nodes, or mistakes in edge transition condition judgments. This requires developers to have a global understanding of the entire graph's operating mechanism.

## 6.6 Chapter Summary

In this chapter, we experienced some of the most cutting-edge agent frameworks through hands-on practice in the form of cases.

We saw that each framework has its own approach to implementing agent construction:

- **AutoGen** abstracts complex collaboration as a multi-role, automatically conducted "group chat," with its core being "driving collaboration through conversation."
- **AgentScope** focuses on the robustness and scalability of industrial-grade applications, providing a solid engineering foundation for building high-concurrency, distributed multi-agent systems.
- **CAMEL** demonstrates how to stimulate deep, autonomous collaboration between two expert agents with minimal code through its lightweight "role-playing" and "inception prompting" paradigm.
- **LangGraph** returns to a more fundamental "state machine" model, giving developers precise control over workflows through explicit graph structures, especially its loop capability, paving the way for building reflective and correctable agents.

Through in-depth analysis of these frameworks, we can distill a design trade-off: **the choice between "emergent collaboration" and "explicit control"**. AutoGen and CAMEL rely more on defining agents' "roles" and "goals," allowing complex collaborative behaviors to "emerge" from simple conversation rules. This approach is closer to human interaction patterns but is sometimes difficult to predict and debug. LangGraph requires developers to explicitly define every step and transition condition, sacrificing some "emergent" surprises in exchange for high reliability, controllability, and observability. At the same time, AgentScope reveals a second equally important dimension: **engineering**. Regardless of which collaboration paradigm we choose, to push it from experimental prototype to production application, we must face engineering challenges such as concurrency, fault tolerance, and distributed deployment. AgentScope was born to solve these problems, representing the critical leap from "can run" to "can serve stably."

In summary, there is not just one way to build agents. Deeply understanding the framework design philosophies explored in this chapter can make us not only better "tool users" but also understand the various pros and cons and trade-offs in framework design.

In the next chapter, we will enter the core content of this tutorial, building our own agent framework from scratch, integrating all theory and practice.


## Exercises

1. This chapter introduced four distinctive agent frameworks: `AutoGen`, `AgentScope`, `CAMEL`, and `LangGraph`. Please analyze:

   - In Table 6.1 of Section 6.1.2, multiple dimensions of these four frameworks were compared. Please select the two frameworks you are most familiar with and further compare them in depth from three dimensions: "collaboration mode," "control method," and "applicable scenarios."
   - This chapter mentioned the trade-off between "emergent collaboration" and "explicit control." How do you understand the meaning of these two design philosophies?

2. In the `AutoGen` case in Section 6.2, we built a "software development team." Please extend your thinking based on this case:

   > **Hint**: This is a hands-on practice question, actual operation is recommended

   - The current team uses `RoundRobinGroupChat` (round-robin group chat) mode, where agents speak in a fixed order. If requirements change and the engineer's code needs to be returned to the product manager for re-review, how should the collaboration process be modified? Please design a mechanism that supports "dynamic rollback."
   - In the case, we defined the role and responsibilities of each agent through `System Message`. Please try to add a new role "Quality Assurance" to this team and design its system message so that it can perform automated testing after code review.
   - `AutoGen`'s conversational collaboration has potential instability, which may cause conversations to deviate from the topic or fall into loops. Please think: How to design a "conversation quality monitoring" mechanism to intervene in time when anomalies are detected?

3. In the `AgentScope` case in Section 6.3, we implemented a "Three Kingdoms Werewolf" game. Please analyze in depth:

   - The case used `MsgHub` (message center) to manage communication between agents. Please explain what advantages message-driven architecture has compared to traditional function calls? In what scenarios is this architecture particularly valuable?
   - The game used structured output (such as `DiscussionModelCN`, `WitchActionModelCN`) to constrain agent behavior. Please design a new game role "Hunter" and define its corresponding structured output model, including field definitions and validation rules.
   - `AgentScope` supports distributed deployment, which means different agents can run on different servers. Please think: In a real-time game scenario like "Three Kingdoms Werewolf," what technical challenges will distributed deployment bring? How to ensure message ordering and consistency?

4. In the `CAMEL` case in Section 6.4, we had a psychologist and writer collaborate to create an e-book.

   - In the case, collaboration is forcibly terminated when the `<CAMEL_TASK_DONE>` flag is detected. But what if the two agents disagree (one thinks it can be terminated, one thinks it shouldn't) and cannot reach consensus? Please design a "conflict resolution" compatibility mechanism.
   - `CAMEL` was originally designed for two-agent collaboration but has now been extended to support multi-agent. Please consult `CAMEL`'s latest documentation to understand its multi-agent collaboration module [`workforce`](https://docs.camel-ai.org/key_modules/workforce), and explain how it differs from `AutoGen`'s group chat mode in combination with the architecture diagram.

5. In the `LangGraph` case in Section 6.5, we built a "three-step Q&A assistant." Please analyze:

   - `LangGraph` models the agent process as a state machine and directed graph. Please draw the graph structure of the "understand-search-answer" process in the case, marking nodes, edges, and state transition conditions.
   - The current assistant is a linear process. Please extend this case by adding a "reflection" node: if the generated answer quality is low (e.g., too brief or lacking details), the system should re-search or regenerate the answer. Please design the conditional edge logic for this loop mechanism.
   - `LangGraph`'s advantage lies in native support for loops. Please design a more complex application scenario that fully utilizes this feature: for example, "code generation-testing-fixing" loop, "paper writing-review-revision" loop, etc. Draw the complete graph structure and explain the function of key nodes.

6. Framework selection is one of the key decisions in agent product development. Suppose you are a technical architect at an `AI` company, and the company plans to develop the following three agent product applications. Please select the most suitable framework for each application (`AutoGen`, `AgentScope`, `CAMEL`, `LangGraph`, or develop from scratch without a framework) and explain in detail:

   **Application A**: Intelligent customer service system, needs to handle a large number of concurrent user requests (1000+ per second), requires response time less than 2 seconds, system needs to run stably 7×24 hours, and support horizontal scaling.

   **Application B**: Scientific research paper writing assistance platform, needs a "researcher agent" and a "writer agent" to collaborate deeply, jointly completing literature review, experimental design, data analysis, and paper writing. Requires agents to conduct multiple rounds of in-depth discussion and autonomously advance tasks.

   **Application C**: Financial risk control approval system, needs to process loan applications according to strict procedures: document review → risk assessment → quota calculation → compliance check → manual review → final decision. Each link has clear judgment criteria and branch logic, requiring traceable and auditable processes.


## References

[1] Wu Q, Bansal G, Zhang J, et al. Autogen: Enabling next-gen LLM applications via multi-agent conversations[C]//First Conference on Language Modeling. 2024.

[2] Gao D, Li Z, Pan X, et al. Agentscope: A flexible yet robust multi-agent platform[J]. arXiv preprint arXiv:2402.14034, 2024.

[3] Li G, Hammoud H, Itani H, et al. Camel: Communicative agents for" mind" exploration of large language model society[J]. Advances in Neural Information Processing Systems, 2023, 36: 51991-52008.

[4] LangChain. LangGraph [EB/OL]. (2024). https://github.com/langchain-ai/langgraph.

[5] Microsoft. AutoGen - UserProxyAgent [EB/OL]. (2024). https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.UserProxyAgent.

