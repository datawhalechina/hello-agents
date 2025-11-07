# Chapter 1: Introduction to Agents

Welcome to the world of agents! In today's era where the wave of artificial intelligence is sweeping across the globe, **Agents** have become one of the core concepts driving technological transformation and application innovation. Whether your aspiration is to become a researcher or engineer in the AI field, or you hope to deeply understand the cutting edge of technology as an observer, mastering the essence of agents will be an indispensable part of your knowledge system.

Therefore, in this chapter, let's return to the fundamentals and explore several questions together: What is an agent? What are its main types? How does it interact with the world we live in? Through these discussions, we hope to lay a solid foundation for your future learning and exploration.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-0.png" alt="Figure description" width="90%"/>
  <p>Figure 1.1 Basic interaction loop between agent and environment</p>
</div>

## 1.1 What is an Agent?

When exploring any complex concept, it's best to start with a concise definition. In the field of artificial intelligence, an agent is defined as any entity that can perceive its **Environment** through **Sensors**, and **autonomously** take **Actions** through **Actuators** to achieve specific goals.

This definition contains four fundamental elements of an agent's existence. The environment is the external world in which the agent operates. For an autonomous vehicle, the environment is the dynamically changing road traffic; for a trading algorithm, the environment is the ever-changing financial market. The agent is not isolated from the environment—it continuously perceives the environmental state through its sensors. Cameras, microphones, radar, or data streams returned by various **Application Programming Interfaces (APIs)** are all extensions of its perceptual capabilities.

After acquiring information, the agent needs to take actions to influence the environment, changing its state through actuators. Actuators can be physical devices (such as robotic arms or steering wheels) or virtual tools (such as executing code or calling a service).

However, what truly endows an agent with "intelligence" is its **Autonomy**. An agent is not merely a program that passively responds to external stimuli or strictly executes preset instructions; it can make independent decisions based on its perceptions and internal state to achieve its design goals. This closed loop from perception to action forms the foundation of all agent behavior, as shown in Figure 1.1.

### 1.1.1 Agents from a Traditional Perspective

Before the current wave of **Large Language Models (LLMs)**, pioneers in artificial intelligence had already spent decades exploring and building the concept of "agents." These paradigms, which we now call "traditional agents," are not a single static concept but have undergone a clear evolutionary path from simple to complex, from passive reaction to active learning.

The starting point of this evolution is the structurally simplest **Simple Reflex Agent**. Their decision-making core consists of "condition-action" rules explicitly designed by engineers, as shown in Figure 1.2. A classic automatic thermostat works this way: if the sensor perceives that the room temperature is higher than the set value, it activates the cooling system.

This type of agent relies entirely on current perceptual input and has no memory or predictive capability. It's like a digitized instinct—reliable and efficient, but therefore unable to handle complex tasks that require understanding context. Its limitations raise a key question: What should an agent do if the current state of the environment is insufficient as the sole basis for decision-making?

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-1.png" alt="Figure description" width="90%"/>
  <p>Figure 1.2 Decision logic diagram of a simple reflex agent</p>
</div>

To answer this question, researchers introduced the concept of "state" and developed **Model-Based Reflex Agents**. This type of agent has an internal **World Model** used to track and understand aspects of the environment that cannot be directly perceived. It attempts to answer: "What is the world like now?" For example, an autonomous vehicle driving through a tunnel, even if its camera temporarily cannot perceive the vehicle ahead, its internal model will still maintain a judgment about that vehicle's existence, speed, and estimated position. This internal model gives the agent a primitive form of "memory," making its decisions no longer solely dependent on instantaneous perception but based on a more coherent and complete understanding of the world state.

However, merely understanding the world is not enough—an agent needs clear goals. This led to the development of **Goal-Based Agents**. Unlike the previous two types, their behavior is no longer passively reacting to the environment but actively and proactively selecting actions that can lead to a specific future state. The question this type of agent needs to answer is: "What should I do to achieve my goal?" A classic example is a GPS navigation system: your goal is to reach the office, and the agent will plan an optimal route using search algorithms (such as A*) based on map data (world model). The core capability of this type of agent is reflected in its consideration and planning for the future.

Going further, real-world goals are often not singular. We not only want to reach the office but also want the shortest time, the most fuel-efficient route, and to avoid congestion. When multiple goals need to be balanced, **Utility-Based Agents** emerge. They assign a utility value to every possible world state, representing the level of satisfaction. The agent's core goal is no longer simply to achieve a specific state but to maximize expected utility. It needs to answer a more complex question: "Which behavior will bring me the most satisfactory result?" This architecture allows the agent to learn to balance conflicting goals, making its decisions closer to human rational choice.

So far, the agents we've discussed, although increasingly complex in functionality, still rely on the prior knowledge of human designers for their core decision-making logic, whether rules, models, or utility functions. What if an agent could learn autonomously through interaction with the environment without relying on presets?

This is the core idea of **Learning Agents**, and **Reinforcement Learning (RL)** is the most representative path to realizing this idea. A learning agent contains a performance element (the various types of agents we discussed earlier) and a learning element. The learning element continuously modifies the performance element's decision-making strategy by observing the results of the performance element's actions in the environment.

Imagine an AI learning to play chess. It might start by making random moves, but when it finally wins a game, the system gives it a positive reward. Through extensive self-play, the learning element gradually discovers which moves are more likely to lead to ultimate victory. AlphaGo is a milestone achievement of this philosophy. In the complex game of Go, through reinforcement learning, it discovered many effective strategies that surpass existing human knowledge.

From simple thermostats to cars with internal models, to navigation that can plan routes, to decision-makers who know how to weigh pros and cons, and finally to learners who can self-evolve through experience. This evolutionary path demonstrates the development trajectory that traditional artificial intelligence has undergone in building machine intelligence. They have laid a solid and necessary foundation for our understanding of more cutting-edge agent paradigms today.

### 1.1.2 New Paradigm Driven by Large Language Models

The emergence of large language models represented by **GPT (Generative Pre-trained Transformer)** is significantly changing the construction methods and capability boundaries of agents. LLM agents driven by large language models have fundamentally different core decision-making mechanisms from traditional agents, thus endowing them with a series of entirely new characteristics.

This transformation can be clearly seen from the comparison of the two in multiple dimensions such as core engine, knowledge source, and interaction method, as shown in Table 1.1. In short, the capabilities of traditional agents stem from engineers' explicit programming and knowledge construction, and their behavior patterns are deterministic and bounded; while LLM agents, through pre-training on massive data, have acquired implicit world models and powerful emergent capabilities, enabling them to handle complex tasks in a more flexible and general way.

<div align="center">
  <p>Table 1.1 Core comparison between traditional agents and LLM-driven agents</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-2.png" alt="Figure description" width="90%"/>
</div>

This difference enables LLM agents to directly process high-level, ambiguous, and context-rich natural language instructions. Let's use an "intelligent travel assistant" as an example to illustrate.

Before the emergence of LLM agents, planning a trip typically meant users needed to manually switch between multiple dedicated applications (such as weather, maps, booking websites), with the user themselves playing the role of information integration and decision-making. An LLM agent, however, can integrate this process. When receiving an ambiguous instruction like "plan a trip to Xiamen," its working method reflects the following points:

- **Planning and Reasoning**: The agent first decomposes this high-level goal into a series of logical subtasks, for example: `[Confirm travel preferences] -> [Query destination information] -> [Draft itinerary] -> [Book tickets and accommodation]`. This is an internal, model-driven planning process.
- **Tool Use**: When executing the plan, the agent identifies information gaps and proactively calls external tools to fill them. For example, it will call a weather query interface to get real-time weather, and based on the information "rain is forecast," it will tend to recommend indoor activities in subsequent planning.
- **Dynamic Adjustment**: During the interaction, the agent treats user feedback (such as "this hotel exceeds the budget") as new constraints and adjusts subsequent actions accordingly, re-searching and recommending options that meet the new requirements. The entire process of "**check weather → adjust itinerary → book hotel**" demonstrates its ability to dynamically modify its behavior based on context.

In summary, we are shifting from developing specialized automation tools to building systems that can autonomously solve problems. The core is no longer writing code but guiding a general "brain" to plan, act, and learn.

### 1.1.3 Types of Agents

Following the review of agent evolution above, this section will classify agents from three complementary dimensions.

(1) **Classification Based on Internal Decision Architecture**

The first classification dimension is based on the complexity of the agent's internal decision architecture. This perspective was systematically proposed in "Artificial Intelligence: A Modern Approach"<sup>[1]</sup>. As described in Section 1.1.1, the evolutionary path of traditional agents itself constitutes the most classic classification ladder, covering from simple **reactive** agents to **model-based** agents that introduce internal models, and then to more forward-looking **goal-based** and **utility-based** agents. Additionally, **learning capability** is a meta-capability that can be endowed to all the above types, enabling them to self-improve through experience.

(2) **Classification Based on Time and Reactivity**

In addition to the complexity of internal architecture, agents can also be classified from the time dimension of decision-making processing. This perspective focuses on whether an agent acts immediately after receiving information or acts after deliberate planning. This reveals a core trade-off in agent design: the balance between **Reactivity**, which pursues speed, and **Deliberation**, which pursues optimal solutions, as shown in Figure 1.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-3.png" alt="Figure description" width="90%"/>
  <p>Figure 1.3 Relationship between agent decision time and quality</p>
</div>

- **Reactive Agents**

This type of agent makes nearly instantaneous responses to environmental stimuli with extremely low decision latency. They typically follow a direct mapping from perception to action, with no or minimal future planning. The **simple reactive** and **model-based** agents mentioned above belong to this category.

Their core advantage lies in **fast speed and low computational overhead**, which is crucial in dynamic environments requiring rapid decision-making. For example, a vehicle's airbag system must react within milliseconds of a collision—any delay could lead to serious consequences; similarly, high-frequency trading robots must rely on reactive decision-making to capture fleeting market opportunities. However, the cost of this speed is "short-sightedness." Due to lack of long-term planning, reactive agents easily fall into local optima and struggle to complete complex tasks requiring multi-step coordination.

- **Deliberative Agents**

In contrast to reactive agents, deliberative (or planning) agents engage in complex thinking and planning before acting. They do not immediately react to perceptions but first use their internal world model to systematically explore various future possibilities, evaluate the consequences of different action sequences, in hopes of finding an optimal path to achieve goals. **Goal-based** and **utility-based** agents are typical deliberative agents.

Their decision-making process can be likened to a chess player. They don't just look at the immediate move but anticipate possible opponent responses and plan out subsequent moves, even dozens of moves ahead. This deliberative capability enables them to handle complex tasks requiring long-term vision, such as formulating a business plan or planning a long-distance trip. Their advantage lies in the strategic nature and foresight of their decisions. However, the flip side of this advantage is high time and computational costs. In rapidly changing environments, when a deliberative agent is still deep in thought, the best moment to act may have long passed.

- **Hybrid Agents**

Complex tasks in the real world often require both immediate reactions and long-term planning. For example, the intelligent travel assistant we mentioned earlier needs to adjust recommendations based on user's immediate feedback (such as "this hotel is too expensive") (reactivity), while also being able to plan a complete multi-day travel itinerary (deliberation). Therefore, hybrid agents emerged, aiming to combine the advantages of both and achieve a balance between reaction and planning.

A classic hybrid architecture is hierarchical design: the lower layer is a fast reactive module that handles emergencies and basic actions; the upper layer is a deliberative planning module responsible for formulating long-term goals. Modern LLM agents demonstrate a more flexible hybrid mode. They typically operate in a "think-act-observe" loop, cleverly integrating both modes:

- **Reasoning**: In the "thinking" phase, the LLM analyzes the current situation and plans the next reasonable action. This is a deliberative process.
- **Acting & Observing**: In the "acting" and "observing" phases, the agent interacts with external tools or the environment and immediately receives feedback. This is a reactive process.

Through this approach, the agent decomposes a grand task requiring long-term planning into a series of "planning-reaction" micro-loops. This enables it to flexibly respond to immediate environmental changes while ultimately completing complex long-term goals through coherent steps.

**(3) Classification Based on Knowledge Representation**

This is a more fundamental classification dimension that explores what form the knowledge used by agents for decision-making exists in their "minds." This question is at the core of a debate that has lasted more than half a century in the field of artificial intelligence and has shaped two distinctly different AI cultures.

- **Symbolic AI**

Symbolism, often called traditional artificial intelligence, has a core belief: intelligence stems from logical operations on symbols. The symbols here are human-readable entities (such as words, concepts), and operations follow strict logical rules, as shown on the left side of Figure 1.4. This is like a meticulous librarian organizing world knowledge into clear rule bases and knowledge graphs.

Its main advantage lies in transparency and interpretability. Since reasoning steps are explicit, its decision-making process can be fully traced, which is crucial in high-risk fields such as finance and healthcare. However, its "Achilles' heel" lies in fragility: it relies on a complete rule system, but in the real world full of ambiguity and exceptions, any new situation not covered can lead to system failure, which is the so-called "knowledge acquisition bottleneck."

- **Sub-symbolic AI**

Sub-symbolism, or connectionism, provides a completely different picture. Here, knowledge is not explicit rules but implicitly distributed in a complex network composed of numerous neurons, representing statistical patterns learned from massive data. Neural networks and deep learning are its representatives.

As shown in the middle of Figure 1.4, if symbolic AI is a librarian, then sub-symbolic AI is like a babbling child. They don't learn to recognize cats by learning rules like "cats have four legs, are furry, and meow," but after seeing thousands of cat pictures, the neural network in their brain can identify the visual pattern of the concept "cat." The power of this approach lies in its pattern recognition capability and robustness to noisy data. It can easily handle unstructured data such as images and sounds, which are extremely difficult tasks for symbolic AI.

However, this powerful intuitive capability also comes with opacity. Sub-symbolic systems are typically viewed as a **Black Box**. It can identify a cat in a picture with amazing accuracy, but if you ask it "why do you think this is a cat?", it likely cannot provide a logically sound explanation. Additionally, it performs poorly on pure logical reasoning tasks and sometimes produces hallucinations that seem reasonable but are factually incorrect.

- **Neuro-Symbolic AI**

For a long time, the two camps of symbolism and sub-symbolism developed like two parallel lines. To overcome the limitations of the above two paradigms, a "grand reconciliation" idea began to emerge, which is neuro-symbolic AI, also called neuro-symbolic hybrid. Its goal is to merge the advantages of both paradigms, creating a hybrid agent that can both learn from data like neural networks and perform logical reasoning like symbolic systems. It attempts to bridge the gap between perception and cognition, intuition and rationality. Nobel Prize-winning economist Daniel Kahneman's dual-system theory proposed in his book "Thinking, Fast and Slow" provides an excellent analogy for understanding neuro-symbolism<sup>[2]</sup>, as shown in Figure 1.4:

- **System 1** is a fast, intuitive, parallel thinking mode, similar to the powerful pattern recognition capability of sub-symbolic AI.
- **System 2** is slow, methodical, logic-based deliberative thinking, just like the reasoning process of symbolic AI.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-4.png" alt="Figure description" width="90%"/>
  <p>Figure 1.4 Knowledge representation paradigms of symbolism, sub-symbolism, and neuro-symbolic hybrid</p>
</div>

Human intelligence stems from the collaborative work of these two systems. Similarly, a truly robust AI also needs to combine the strengths of both. Large language model-driven agents are an excellent practical example of neuro-symbolism. Its core is a huge neural network, giving it pattern recognition and language generation capabilities. However, when it works, it generates a series of structured intermediate steps, such as thoughts, plans, or API calls, which are all explicit, operable symbols. Through this approach, it achieves a preliminary fusion of perception and cognition, intuition and rationality.

## 1.2 Composition and Operating Principles of Agents

### 1.2.1 Task Environment Definition

To understand how an agent operates, we must first understand the **task environment** in which it operates. In the field of artificial intelligence, the **PEAS model** is typically used to precisely describe a task environment, analyzing its **Performance measure, Environment, Actuators, and Sensors**. Taking the intelligent travel assistant mentioned above as an example, Table 1.2 below shows how to use the PEAS model to specify its task environment.

<div align="center">
  <p>Table 1.2 PEAS description of intelligent travel assistant</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-6.png" alt="Figure description" width="90%"/>
</div>

In practice, the digital environment in which LLM agents operate exhibits several complex characteristics that directly affect agent design.

First, the environment is typically **partially observable**. For example, when a travel assistant queries flights, it cannot obtain all real-time seat information from all airlines at once. It can only see partial data returned by the flight booking API it calls, which requires the agent to have memory (remembering queried routes) and exploration (trying different query dates) capabilities.

Second, the results of actions are not always deterministic. Based on the predictability of results, environments can be divided into **deterministic** and **stochastic**. The task environment of a travel assistant is a typical stochastic environment. When it searches for ticket prices, two adjacent calls may return different ticket prices and remaining seat numbers, requiring the agent to have the ability to handle uncertainty, monitor changes, and make timely decisions.

Additionally, there may be other actors in the environment, forming a **multi-agent** environment. For a travel assistant, other users' booking behaviors, other automated scripts, and even airlines' dynamic pricing systems are all other "agents" in the environment. Their actions (for example, booking the last discounted ticket) directly change the state of the environment in which the travel assistant operates, placing higher demands on the agent's rapid response and strategy selection.

Finally, almost all tasks occur in **sequential** and **dynamic** environments. "Sequential" means current actions affect the future; while "dynamic" means the environment itself may change while the agent is making decisions. This requires the agent's "perceive-think-act-observe" loop to be able to quickly and flexibly adapt to a continuously changing world.

### 1.2.2 Agent Operating Mechanism

After defining the task environment in which an agent operates, let's explore its core operating mechanism. An agent does not complete tasks in one go but interacts with the environment through a continuous loop. This core mechanism is called the **Agent Loop**. As shown in Figure 1.5, this loop describes the dynamic interaction process between the agent and the environment, forming the foundation of its autonomous behavior.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-5.png" alt="Figure description" width="90%"/>
  <p>Figure 1.5 Basic loop of agent-environment interaction</p>
</div>

This loop mainly contains the following interconnected stages:

1. **Perception**: This is the starting point of the loop. The agent receives input information from the environment through its sensors (for example, API listening ports, user input interfaces). This information, i.e., **Observation**, can be either the user's initial instruction or feedback on environmental state changes caused by the previous action.
2. **Thought**: After receiving observation information, the agent enters its core decision-making stage. For LLM agents, this is typically an internal reasoning process driven by large language models. As shown in the figure, the "thought" stage can be further subdivided into two key links:
   - **Planning**: Based on current observations and its internal memory, the agent updates its understanding of the task and environment and formulates or adjusts an action plan. This may involve decomposing complex goals into a series of more specific subtasks.
   - **Tool Selection**: Based on the current plan, the agent selects the most suitable tool from its available tool library to execute the next step and determines the specific parameters needed to call that tool.
3. **Action**: After decision-making is complete, the agent executes specific actions through its actuators. This typically manifests as calling a selected tool (such as a code interpreter or search engine API), thereby influencing the environment with the intent to change its state.

Action is not the end of the loop. The agent's action causes a **state change** in the **environment**, which then produces a new **observation** as result feedback. This new observation is captured by the agent's perception system in the next round of the loop, forming a continuous "perceive-think-act-observe" closed loop. It is through continuously repeating this loop that the agent gradually advances the task, evolving from the initial state toward the goal state.

### 1.2.3 Agent Perception and Action

In engineering practice, to enable LLMs to effectively drive this loop, we need a clear **Interaction Protocol** to regulate information exchange between it and the environment.

In many modern agent frameworks, this protocol is embodied in the structured definition of each agent output. The agent's output is no longer a single natural language response but a piece of text following a specific format that explicitly shows its internal reasoning process and final decision.

This structure typically contains two core parts:

- **Thought**: This is a "snapshot" of the agent's internal decision-making. It articulates in natural language how the agent analyzes the current situation, reviews the observation results from the previous step, engages in self-reflection and problem decomposition, and ultimately plans the next specific action.
- **Action**: This is the specific operation the agent decides to impose on the environment based on its thinking, typically expressed as a function call.

For example, an agent planning a trip might generate the following formatted output:

```Bash
Thought: The user wants to know the weather in Beijing. I need to call the weather query tool.
Action: get_weather("Beijing")
```

The `Action` field here constitutes an instruction to the external world. An external **Parser** will capture this instruction and call the corresponding `get_weather` function.

After the action is executed, the environment returns a result. For example, the `get_weather` function might return a JSON object containing detailed weather data. However, raw machine-readable data (such as JSON) typically contains redundant information that the LLM doesn't need to focus on, and the format doesn't conform to its natural language processing habits.

Therefore, an important responsibility of the perception system is to play the role of a sensor: processing and encapsulating this raw output into concise, clear natural language text, i.e., observation.

```Bash
Observation: Beijing's current weather is sunny, temperature 25 degrees Celsius, light breeze.
```

This `Observation` text is fed back to the agent as the main input information for the next round of the loop, for it to conduct a new round of `Thought` and `Action`.

In summary, through this rigorous loop composed of Thought, Action, and Observation, LLM agents can effectively combine their internal language reasoning capabilities with real information and tool operation capabilities from the external environment.

## 1.3 Hands-on Experience: Implementing Your First Agent in 5 Minutes

In the previous sections, we learned about the agent's task environment, core operating mechanism, and the `Thought-Action-Observation` interaction paradigm. While theoretical knowledge is important, the best way to learn is through hands-on practice. In this section, we will guide you to build a working intelligent travel assistant from scratch using a few simple lines of Python code. This process will follow the theoretical loop we just learned, allowing you to intuitively experience how an agent "thinks" and interacts with external "tools." Let's get started!

In this case, our goal is to build an intelligent travel assistant that can handle step-by-step tasks. The user task to be solved is defined as: "Hello, please help me check today's weather in Beijing, and then recommend a suitable tourist attraction based on the weather." To complete this task, the agent must demonstrate clear logical planning capabilities. It needs to first call the weather query tool and use the obtained observation results as the basis for the next step. In the next round of the loop, it then calls the attraction recommendation tool to arrive at the final suggestion.

### 1.3.1 Preparation

To access web APIs from a Python program, we need an HTTP library. `requests` is the most popular and easy-to-use choice in the Python community. `tavily-python` is a powerful AI search API client for obtaining real-time web search results, which can be obtained by registering on the [official website](https://www.tavily.com/). `openai` is the official Python SDK provided by OpenAI for calling large language model services such as GPT. Please install them first with the following command:

```bash
pip install requests tavily-python openai
```

(1) Instruction Template

The key to driving a real LLM lies in **Prompt Engineering**. We need to design an "instruction template" that tells the LLM what role it should play, what tools it has, and how to format its thinking and actions. This is the "manual" for our agent, which will be passed to the LLM as `system_prompt`.

```
AGENT_SYSTEM_PROMPT = """
You are an intelligent travel assistant. Your task is to analyze user requests and use available tools to solve problems step by step.

# Available Tools:
- `get_weather(city: str)`: Query real-time weather for a specified city.
- `get_attraction(city: str, weather: str)`: Search for recommended tourist attractions based on city and weather.

# Action Format:
Your response must strictly follow the following format. First is your thinking process, then the specific action you want to execute. Each response should output only one Thought-Action pair:
Thought: [Here is your thinking process and next step plan]
Action: [Here is the tool you want to call, in the format function_name(arg_name="arg_value")]

# Task Completion:
When you have collected enough information to answer the user's final question, you must use `finish(answer="...")` after the Action: field to output the final answer.

Let's begin!
"""
```

(2) Tool 1: Query Real Weather

We will use the free weather query service `wttr.in`, which can return weather data for a specified city in JSON format. Here is the code to implement this tool:

```python
import requests
import json

def get_weather(city: str) -> str:
    """
    Query real weather information by calling the wttr.in API.
    """
    # API endpoint, we request data in JSON format
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # Make network request
        response = requests.get(url)
        # Check if response status code is 200 (success)
        response.raise_for_status()
        # Parse returned JSON data
        data = response.json()

        # Extract current weather conditions
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # Format as natural language return
        return f"{city} current weather: {weather_desc}, temperature {temp_c} degrees Celsius"

    except requests.exceptions.RequestException as e:
        # Handle network errors
        return f"Error: Network problem encountered when querying weather - {e}"
    except (KeyError, IndexError) as e:
        # Handle data parsing errors
        return f"Error: Failed to parse weather data, city name may be invalid - {e}"
```

(3) Tool 2: Search and Recommend Tourist Attractions

We will define a new tool `search_attraction` that searches the internet for suitable attractions based on city and weather conditions:

```python
import os
from tavily import TavilyClient

def get_attraction(city: str, weather: str) -> str:
    """
    Based on city and weather, use Tavily Search API to search and return optimized attraction recommendations.
    """
    # 1. Read API key from environment variable
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable not configured."

    # 2. Initialize Tavily client
    tavily = TavilyClient(api_key=api_key)

    # 3. Construct a precise query
    query = f"'{city}' most worthwhile tourist attractions and reasons in '{weather}' weather"

    try:
        # 4. Call API, include_answer=True will return a comprehensive answer
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 5. Tavily's returned results are already very clean and can be used directly
        # response['answer'] is a summary answer based on all search results
        if response.get("answer"):
            return response["answer"]

        # If there's no comprehensive answer, format raw results
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
             return "Sorry, no relevant tourist attraction recommendations found."

        return "Based on search, found the following information for you:\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"Error: Problem occurred when executing Tavily search - {e}"
```

Finally, we put all tool functions into a dictionary for the main loop to call:

```python
# Put all tool functions into a dictionary for easy subsequent calling
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}
```

### 1.3.2 Connecting to Large Language Models

Currently, many LLM service providers (including OpenAI, Azure, and numerous open-source model service frameworks such as Ollama, vLLM, etc.) follow interface specifications similar to the OpenAI API. This standardization brings great convenience to developers. The agent's autonomous decision-making capability comes from the LLM. We will implement a universal client `OpenAICompatibleClient` that can connect to any LLM service compatible with the OpenAI interface specification.

```python
from openai import OpenAI

class OpenAICompatibleClient:
    """
    A client for calling any LLM service compatible with the OpenAI interface.
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Call LLM API to generate response."""
        print("Calling large language model...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("Large language model responded successfully.")
            return answer
        except Exception as e:
            print(f"Error occurred when calling LLM API: {e}")
            return "Error: Error occurred when calling language model service."
```

To instantiate this class, you need to provide three pieces of information: `API_KEY`, `BASE_URL`, and `MODEL_ID`. The specific values depend on the service provider you use (such as OpenAI official, Azure, or local models like Ollama). If you don't have access to these yet, you can refer to [1.2 API Setup](https://datawhalechina.github.io/handy-multi-agent/#/chapter1/1.2.api-setup) in another Datawhale tutorial.

### 1.3.3 Executing the Action Loop

The main loop below will integrate all components and drive the LLM to make decisions through formatted prompts.

```python
import re

# --- 1. Configure LLM client ---
# Please replace this with the corresponding credentials and address for the service you use
API_KEY = "YOUR_API_KEY"
BASE_URL = "YOUR_BASE_URL"
MODEL_ID = "YOUR_MODEL_ID"
TAVILY_API_KEY="YOUR_Tavily_KEY"
os.environ['TAVILY_API_KEY'] = "YOUR_TAVILY_API_KEY"

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# --- 2. Initialize ---
user_prompt = "Hello, please help me check today's weather in Beijing, and then recommend a suitable tourist attraction based on the weather."
prompt_history = [f"User request: {user_prompt}"]

print(f"User input: {user_prompt}\n" + "="*40)

# --- 3. Run main loop ---
for i in range(5): # Set maximum number of loops
    print(f"--- Loop {i+1} ---\n")

    # 3.1. Build Prompt
    full_prompt = "\n".join(prompt_history)

    # 3.2. Call LLM for thinking
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    # Truncate extra Thought-Action pairs that the model may generate
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', 
                    llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("Truncated extra Thought-Action pairs")
    print(f"Model output:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3. Parse and execute action
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        print("Parse error: Action not found in model output.")
        break
    action_str = action_match.group(1).strip()

    if action_str.startswith("finish"):
        final_answer = re.search(r'finish\(answer="(.*)"\)', action_str).group(1)
        print(f"Task completed, final answer: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"Error: Undefined tool '{tool_name}'"

    # 3.4. Record observation results
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)
```

Through the above steps, we have built a complete agent driven by a real LLM. Its core lies in the combination of "tools" and "prompt engineering," which is precisely the design essence of current mainstream agent frameworks (such as LangChain, LlamaIndex, etc.).

### 1.3.4 Running Case Analysis

The following output fully demonstrates a successful agent execution process. Through analysis of this three-round loop, we can clearly see the core capabilities of the agent in solving problems.

```bash
User input: Hello, please help me check today's weather in Beijing, and then recommend a suitable tourist attraction based on the weather.
========================================
--- Loop 1 ---

Calling large language model...
Large language model responded successfully.
Model output:
Thought: First need to get Beijing's weather today, then recommend tourist attractions based on the weather.
Action: get_weather(city="Beijing")

Observation: Beijing current weather: Sunny, temperature 26 degrees Celsius
========================================
--- Loop 2 ---

Calling large language model...
Large language model responded successfully.
Model output:
Thought: Now I know Beijing's weather today is sunny with moderate temperature, I can recommend a suitable tourist attraction based on this information.
Action: get_attraction(city="Beijing", weather="Sunny")

Observation: The most worthwhile tourist attractions in Beijing on sunny days are the Summer Palace for its beautiful lake views and ancient architecture. Another recommendation is the Great Wall for its spectacular scenery and historical significance.
========================================
--- Loop 3 ---

Calling large language model...
Large language model responded successfully.
Model output:
Thought: I have obtained two attraction suggestions suitable for sunny days, now I can provide a satisfactory response to the user based on this information.
Action: finish(answer="Today's weather in Beijing is sunny with a temperature of 26 degrees Celsius, very suitable for outdoor activities. I recommend you visit the Summer Palace to enjoy the beautiful lake views and ancient architecture, or go to the Great Wall to experience its spectacular scenery and profound historical significance. Hope you have a pleasant trip!")

Task completed, final answer: Today's weather in Beijing is sunny with a temperature of 26 degrees Celsius, very suitable for outdoor activities. I recommend you visit the Summer Palace to enjoy the beautiful lake views and ancient architecture, or go to the Great Wall to experience its spectacular scenery and profound historical significance. Hope you have a pleasant trip!
```

This simple travel assistant case concentrates on demonstrating the four basic capabilities of an agent based on the `Thought-Action-Observation` paradigm: task decomposition, tool invocation, context understanding, and result synthesis. It is through the continuous iteration of this loop that the agent can transform a vague user intent into a series of specific, executable steps and ultimately achieve the goal.

## 1.4 Collaboration Modes of Agent Applications

In the previous section, we gained a deep understanding of the internal operating loop of an agent by building one ourselves. However, in broader application scenarios, our role is increasingly transforming into users and collaborators. Based on the agent's role in tasks and degree of autonomy, its collaboration modes are mainly divided into two types: one is as an efficient tool deeply integrated into our workflow; the other is as an autonomous collaborator working with other agents to complete complex goals.

### 1.4.1 Agents as Developer Tools

In this mode, agents are deeply integrated into developers' workflows as powerful auxiliary tools. They enhance rather than replace the developer's role, automating tedious, repetitive tasks so developers can focus more on creative core work. This human-machine collaboration approach greatly improves the efficiency and quality of software development.

Currently, the market has seen the emergence of multiple excellent AI programming assistance tools. While they all improve development efficiency, they differ in implementation paths and functional focus:

- **GitHub Copilot**: As one of the most influential products in this field, Copilot was jointly developed by GitHub and OpenAI. It is deeply integrated into mainstream editors such as Visual Studio Code and is renowned for its powerful code auto-completion capabilities. When developers write code, Copilot can provide real-time suggestions for entire lines or even entire function blocks. In recent years, it has also expanded conversational programming capabilities through Copilot Chat, allowing developers to solve programming problems through chat within the editor.
- **Claude Code**: Claude Code is an AI programming assistant developed by Anthropic, designed to help developers efficiently complete coding tasks in the terminal through natural language instructions. It can understand complete codebase structures, perform operations such as code editing, testing, and debugging, and supports full-process development from describing functionality to code implementation. Claude Code also provides a headless mode suitable for CI, pre-commit hooks, build scripts, and other automation scenarios, providing developers with a powerful command-line programming experience.
- **Trae**: As an emerging AI programming tool, Trae focuses on providing developers with intelligent code generation and optimization services. It analyzes code patterns through deep learning technology and can provide developers with precise code suggestions and automated refactoring solutions. Trae's distinctive feature is its lightweight design and fast response capability, particularly suitable for scenarios requiring frequent iteration and rapid prototyping.
- **Cursor**: Unlike the above tools that mainly exist as plugins or integrated features, Cursor has chosen a more integrated path—it is itself an AI-native code editor. Rather than adding AI functionality to existing editors, it made AI interaction a core feature from the design stage. In addition to top-tier code generation and chat capabilities, it emphasizes letting AI understand the context of the entire codebase, thereby achieving deeper Q&A, refactoring, and debugging.

Of course, there are many other excellent tools not listed here, but they all point to a clear trend: AI is deeply integrating into the entire software development lifecycle, profoundly reshaping the efficiency boundaries and development paradigms of software engineering by building efficient human-machine collaborative workflows.

### 1.4.2 Agents as Autonomous Collaborators

Unlike serving as tools to assist humans, the second interaction mode elevates the automation level of agents to an entirely new level: autonomous collaborators. In this mode, we no longer guide AI step-by-step through every action but delegate a high-level goal to it. The agent, like a true project team member, independently plans, reasons, executes, and reflects until finally delivering results. This transformation from assistant to collaborator has brought LLM agents deeper into public view. It marks the evolution of our relationship with AI from "command-execute" to "goal-delegate." Agents are no longer passive tools but active goal pursuers.

Currently, approaches to achieving this autonomous collaboration are flourishing, with numerous excellent frameworks and products emerging, from early BabyAGI and AutoGPT to now more mature frameworks like CrewAI, AutoGen, MetaGPT, and LangGraph, collectively driving rapid development in this field. Although specific implementations vary greatly, their architectural paradigms can be roughly summarized into several mainstream directions:

1. **Single-Agent Autonomous Loop**: This is an early typical paradigm, represented by models like **AgentGPT**. Its core is a general agent that continuously self-prompts and iterates through a "think-plan-execute-reflect" closed loop to complete an open-ended high-level goal.
2. **Multi-Agent Collaboration**: This is currently the most mainstream exploration direction, aiming to solve complex problems by simulating human team collaboration modes. It can be further subdivided into different modes: **Role-Playing Dialogue**: Like the **CAMEL** framework, which assigns clear roles and communication protocols to two agents (for example, "programmer" and "product manager"), allowing them to collaboratively complete tasks in a structured dialogue. **Organized Workflow**: Like **MetaGPT** and **CrewAI**, which simulate a "virtual team" with clear division of labor (such as a software company or consulting group). Each agent has preset responsibilities and workflows (SOPs), collaborating in a hierarchical or sequential manner to produce high-quality complex outputs (such as complete codebases or research reports). **AutoGen** and **AgentScope** provide more flexible dialogue modes, allowing developers to customize complex interaction networks between agents.
3. **Advanced Control Flow Architecture**: Frameworks such as **LangGraph** focus more on providing agents with more powerful underlying engineering foundations. They model the agent's execution process as a state graph, enabling more flexible and reliable implementation of complex processes such as loops, branches, backtracking, and human intervention.

These different architectural paradigms collectively drive autonomous agents from theoretical concepts toward broader practical applications, enabling them to handle increasingly complex real-world tasks. In our subsequent chapters, we will also experience the differences and advantages between different types of frameworks.

### 1.4.3 Differences Between Workflow and Agent

After understanding the two modes of agents as "tools" and "collaborators," it is necessary to discuss the differences between Workflow and Agent. Although both aim to achieve task automation, their underlying logic, core characteristics, and applicable scenarios are fundamentally different.

Simply put, **Workflow makes AI execute instructions step by step, while Agent gives AI freedom to autonomously achieve goals.**

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-18.png" alt="Figure description" width="90%"/>
  <p>Figure 1.6 Differences between Workflow and Agent</p>
</div>

As shown in Figure 1.6, workflow is a traditional automation paradigm whose core is **pre-defined, structured orchestration of a series of tasks or steps**. It is essentially a precise, static flowchart that specifies which operations to execute under what conditions and in what order. A typical case: a company's expense reimbursement approval process. Employee submits reimbursement form (trigger) -> If amount is less than 500 yuan, directly approved by department manager -> If amount is greater than 500 yuan, first approved by department manager, then forwarded to CFO for approval -> After approval, notify finance department to make payment. Every step and every judgment condition of the entire process is precisely preset.

Unlike workflows, agents based on large language models are **autonomous, goal-oriented systems**. They not only execute preset instructions but can also understand the environment to a certain extent, reason, formulate plans, and dynamically take actions to achieve final goals. LLMs play the role of the "brain" in this process. A typical example is the intelligent travel assistant we wrote in Section 1.3. When we give it a new instruction, for example: **"Hello, please help me check today's weather in Beijing, and then recommend a suitable tourist attraction based on the weather."** Its processing fully demonstrates its autonomy:

1. **Planning and Tool Invocation:** The agent first breaks down the task into two steps: ① Query weather; ② Recommend attractions based on weather. Then, it autonomously selects and calls the "weather query API," passing "Beijing" as a parameter.
2. **Reasoning and Decision-Making:** Suppose the API returns "sunny, light breeze." The agent's LLM brain will reason based on this information: "Sunny days are suitable for outdoor activities." Then, based on this judgment, it will filter outdoor attractions in Beijing from its knowledge base or through search engine tools, such as the Forbidden City, Summer Palace, Temple of Heaven Park, etc.
3. **Generate Results:** Finally, the agent will synthesize the information and provide a complete, humanized answer: "Today's weather in Beijing is sunny with a light breeze, very suitable for outdoor activities. I recommend you visit the Summer Palace, where you can boat on Kunming Lake and enjoy the beautiful royal garden scenery."

In this process, there are no hard-coded rules like `if weather=sunny then recommend Summer Palace`. If the weather is "rainy," the agent will autonomously reason and recommend indoor venues such as the National Museum or Capital Museum. **This ability to dynamically reason and make decisions based on real-time information is the core value of agents.**

## 1.4 Chapter Summary

In this chapter, we embarked on an introductory journey to explore agents. Our journey began with the most fundamental questions:

- **What are large language model-driven agents?** We first clarified their definition and understood that modern agents are entities with capabilities. They are no longer just scripts executing preset programs but decision-makers capable of autonomous reasoning and tool use.
- **How do agents work?** We delved into the operating mechanism of agent-environment interaction. We learned that this continuous closed loop is the foundation for agents to process information, make decisions, influence the environment, and adjust their behavior based on feedback.
- **How to build an agent?** This was the practical core of this chapter. Using the "intelligent travel assistant" as an example, we built a complete agent driven by a real LLM.
- **What are the mainstream application paradigms of agents?** Finally, we cast our vision toward broader application domains. We explored two mainstream agent interaction modes: one is "developer tools" represented by GitHub Copilot and Cursor that enhance human workflows; the other is "autonomous collaborators" represented by frameworks like CrewAI, MetaGPT, and AgentScope that can independently complete high-level goals. We also explained the differences between Workflow and Agent.

Through this chapter's learning, we have established a foundational cognitive framework about agents. So, how did it evolve step by step from its initial conception to the present? In the next chapter, we will explore the development history of agents—a journey to trace back to the origins is about to begin!

## Exercises

> **Note**: Some of the following exercises do not have standard answers. The focus is on cultivating learners' critical in-depth thinking and hands-on practical abilities regarding agent systems.

1. Please analyze whether the **subject** in the following four `cases` qualifies as an agent. If so, what type of agent does it belong to (can be analyzed from multiple classification dimensions), and explain your reasoning:

   `Case A`: **A supercomputer conforming to von Neumann architecture**, with peak computing power of up to 2 EFlops per second

   `Case B`: **Tesla's autonomous driving system** is driving on a highway when it suddenly detects an obstacle ahead and needs to make a braking or lane-change decision within milliseconds

   `Case C`: **AlphaGo** is playing against a human player and needs to evaluate the current situation and plan the optimal strategy for dozens of moves ahead

   `Case D`: **ChatGPT acting as an intelligent customer service** is handling a user complaint and needs to query order information, analyze the problem cause, provide solutions, and soothe user emotions

2. Suppose you need to design a task environment for an "intelligent fitness coach." This agent can:
   - Monitor users' physiological data such as heart rate and exercise intensity through wearable devices
   - Dynamically adjust training plans based on users' fitness goals (fat loss/muscle gain/endurance improvement)
   - Provide real-time voice guidance and motion correction during user exercise
   - Evaluate training effectiveness and provide dietary recommendations

   Please use the PEAS model to completely describe this agent's task environment and analyze what characteristics this environment has (such as partially observable, stochastic, dynamic, etc.).

3. An e-commerce company is considering two approaches to handle after-sales refund requests:

   Approach A (`Workflow`): Design a fixed process, for example:

   A.1 For general products within 7 days, amounts `< 100 RMB` are automatically approved; `100-500 RMB` are reviewed by customer service; `> 500 RMB` require supervisor approval; special products (such as customized items) are always rejected

   A.2 For products beyond 7 days, regardless of amount, they can only be reviewed by customer service or approved by supervisors;

   Approach B (`Agent`): Build an agent system that understands refund policies, analyzes user historical behavior, evaluates product conditions, and autonomously decides whether to approve refunds

   Please analyze:
   - What are the advantages and disadvantages of these two approaches?
   - Under what circumstances is `Workflow` more suitable? When does `Agent` have advantages? If you were the head of this e-commerce company, which approach would you prefer?
   - Is there an Approach C that can combine both approaches to achieve complementary strengths?

4. Based on the intelligent travel assistant in Section 1.3, please consider how to add the following features (you can just describe the design ideas or further attempt code implementation):

   > **Hint**: Think about how to modify the `Thought-Action-Observation` loop to implement these features.

   - Add a "memory" feature that allows the agent to remember user preferences (such as liking historical and cultural attractions, budget range, etc.)
   - When recommended attraction tickets are sold out, the agent can automatically recommend alternative options
   - If the user consecutively rejects 3 recommendations, the agent can reflect and adjust its recommendation strategy

5. Kahneman's "System 1" (fast intuition) and "System 2" (slow reasoning) theory<sup>[2]</sup> provides a good analogy for neuro-symbolic AI. Please first conceive a specific agent application scenario, then explain in the scenario:

   > **Hint**: Medical diagnosis assistants, legal consulting robots, financial risk control systems, etc., are all common application scenarios

   - Which tasks should be handled by "System 1"?
   - Which tasks should be handled by "System 2"?
   - How do these two systems work together to achieve the final goal?

6. Although large language model-driven agent systems demonstrate powerful capabilities, they still have many limitations. Please analyze the following questions:
   - Why do agents or agent systems sometimes produce "hallucinations" (generating seemingly reasonable but actually incorrect information)?
   - In the case in Section 1.3, we set the maximum number of loops to 5. Without this limit, what problems might the agent encounter?
   - How to evaluate an agent's "intelligence" level? Is using only accuracy metrics sufficient?

## References

[1] RUSSELL S, NORVIG P. Artificial Intelligence: A Modern Approach[M]. 4th ed. London: Pearson, 2020.

[2] KAHNEMAN D. Thinking, Fast and Slow[M]. New York: Farrar, Straus and Giroux, 2011.

---

## 💬 Discussion & Communication

Have questions while learning this chapter? Want to share insights with other learners?

**📝 Visit GitHub Discussions:**
- [💬 Exercises Discussion & Q&A](https://github.com/datawhalechina/Hello-Agents/discussions)
- Here you can:
  - ✅ Ask questions about exercises
  - ✅ Share your solutions and ideas
  - ✅ Exchange experiences with other learners
  - ✅ Get help and feedback from the community

**💡 Tip:** There's also a comment section at the bottom of each page for direct discussion!

---