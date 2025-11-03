<div align="right">
  English | <a href="./第十五章%20构建赛博小镇.md">中文</a>
</div>

# Chapter 15: Building Cyber Town

In this chapter, we will explore a brand new direction: **combining agent technology with game engines to build an AI town full of vitality**.

Do you remember those lifelike NPCs in "The Sims" or "Animal Crossing"? They have their own personalities, memories, and social relationships. The Cyber Town in this chapter will be a similar project, but unlike traditional games, our NPCs have real "intelligence" - they can understand player conversations, remember past interactions, and react differently based on affection levels. The Cyber Town in this chapter includes the following core features:

**(1) Intelligent NPC Dialogue System**: Players can have natural language conversations with NPCs, and NPCs will respond based on their role settings and memories.

**(2) Memory System**: NPCs have short-term and long-term memory, able to remember interaction history with players.

**(3) Affection System**: NPC attitudes towards players change with interactions, from stranger to familiar, from friendly to intimate.

**(4) Gamified Interaction**: Players can move freely in a 2D pixel-style office scene and interact with different NPCs.

**(5) Real-Time Logging System**: All conversations and interactions are recorded for easy debugging and analysis.

## 15.1 Project Overview and Architecture Design

### 15.1.1 Why Build an AI Town

NPCs in traditional games can usually only say fixed lines or have limited interactions through preset dialogue trees. Even in the most complex RPG games, NPC dialogues are pre-written by scriptwriters. This approach is controllable but lacks real "intelligence" and "vitality".

Imagine if NPCs in games could understand anything you say, no longer limited to preset options. You can communicate with NPCs in natural language. NPCs will remember what you said last time, your relationship, and even your preferences. Each NPC has their own profession, personality, and speaking style. NPC attitudes towards you change with interactions, from strangers to friends, even close friends.

This is the new possibility that AI technology brings to games. By combining large language models with game engines, we can create NPCs that are truly "alive". This is not just a technical demonstration, but an exploration of future game forms. In educational games, NPCs can play historical figures and scientists, conducting interactive teaching with students. In virtual offices, NPCs can play colleagues and mentors, providing help and advice. NPCs can also serve as companions, conducting emotional communication with users, applied in mental health fields. Of course, the most direct application is to add AI NPCs to traditional games to enhance player experience.

### 15.1.2 Technical Architecture Overview

Cyber Town adopts a **game engine + back-end service** separation architecture, divided into four layers, as shown in Figure 15.1.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-1.png" alt="" width="85%"/>
  <p>Figure 15.1 Cyber Town Technical Architecture</p>
</div>

The front-end layer uses the Godot 4.5 game engine, responsible for game rendering, player control, NPC display, and dialogue UI. Godot is an open-source 2D/3D game engine, very suitable for quickly developing pixel-style games. The back-end layer uses the FastAPI framework, responsible for API routing, NPC state management, dialogue processing, and logging. FastAPI is a modern Python web framework with excellent performance and easy development. The agent layer uses our own HelloAgents framework, responsible for NPC intelligence, memory management, and affection calculation. Each NPC is a SimpleAgent instance with independent memory and state. The external service layer provides LLM capabilities, vector storage, and data persistence, including LLM API, Qdrant vector database, and SQLite relational database.

The data flow process is shown in Figure 15.2:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-2.png" alt="" width="85%"/>
  <p>Figure 15.2 Data Flow Process</p>
</div>

Players press the E key in Godot to interact with NPCs, and Godot sends dialogue requests to the FastAPI back-end via HTTP API. The back-end calls HelloAgents' SimpleAgent to process the dialogue, the Agent retrieves relevant history from the memory system, and then calls the LLM to generate a reply. The back-end updates NPC state and affection, records logs to console and file, and finally returns the reply to the Godot front-end. Godot displays the NPC reply and updates the UI, completing a complete interaction loop.

The project structure is as follows, making it easy for you to locate the source code:

```
Helloagents-AI-Town/
├── helloagents-ai-town/           # Godot game project
│   ├── project.godot              # Godot project configuration
│   ├── scenes/                    # Game scenes
│   │   ├── main.tscn              # Main scene (office)
│   │   ├── player.tscn            # Player character
│   │   ├── npc.tscn               # NPC character
│   │   └── dialogue_ui.tscn       # Dialogue UI
│   ├── scripts/                   # GDScript scripts
│   │   ├── main.gd                # Main scene logic
│   │   ├── player.gd              # Player control
│   │   ├── npc.gd                 # NPC behavior
│   │   ├── dialogue_ui.gd         # Dialogue UI logic
│   │   ├── api_client.gd          # API client
│   │   └── config.gd              # Configuration management
│   └── assets/                    # Game assets
│       ├── characters/            # Character sprites
│       ├── interiors/             # Interior scenes
│       ├── ui/                    # UI materials
│       └── audio/                 # Sound effects and music
│
└── backend/                       # Python back-end
    ├── main.py                    # FastAPI main program
    ├── agents.py                  # NPC Agent system
    ├── relationship_manager.py    # Affection management
    ├── state_manager.py           # State management
    ├── logger.py                  # Logging system
    ├── config.py                  # Configuration management
    ├── models.py                  # Data models
    ├── requirements.txt           # Python dependencies
    └── .env.example               # Environment variable example
```

Detailed architecture design and data flow will be introduced in subsequent sections.

### 15.1.3 Quick Experience: Run the Project in 5 Minutes

Before diving into implementation details, let's first run the project to see the final result. This way you'll have an intuitive understanding of the entire system.

**Environment Requirements:**

- Godot 4.2 or higher
- Python 3.10 or higher
- LLM API key (OpenAI, DeepSeek, Zhipu, etc.)

**Get the Project:**

You can check `code/chapter15/Helloagents-AI-Town`, or clone the complete hello-agents repository from GitHub.

**Start the Back-End:**

```bash
# 1. Enter backend directory
cd Helloagents-AI-Town/backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env file, fill in your API key

# 4. Start back-end service
python main.py
```

After successful startup, you will see the following output:

```
============================================================
🎮 Cyber Town back-end service starting...
============================================================
✅ All services started!
📡 API address: http://0.0.0.0:8000
📚 API documentation: http://0.0.0.0:8000/docs
============================================================
```

**Start Godot:**

Godot installation is very simple. Windows provides a direct `.exe` file, and Mac also provides a `.dmg` file. You can download directly from the official website ([Windows](https://godotengine.org/download/windows/) / [Mac](https://godotengine.org/download/macos/))

Open the Godot engine, click the "Import" button, browse to `Helloagents-AI-Town/helloagents-ai-town/project.godot`, and click "Import and Edit". After Godot imports the resources, press `F5` or click the "Run" button to start the game.

**Experience Core Features:**

After the game starts, you will see a pixel-style Datawhale office scene, as shown in Figure 15.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-3.png" alt="" width="85%"/>
  <p>Figure 15.3 Cyber Town Game Scene</p>
</div>

Use WASD keys to move the player character. When you walk near an NPC, the screen will display a "Press E to interact" prompt. After pressing the E key, a dialogue box will pop up, and you can enter anything you want to say, as shown in Figure 15.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-4.png" alt="" width="85%"/>
  <p>Figure 15.4 Dialogue Interface with NPC</p>
</div>

NPCs will respond based on their role settings (Python engineer, product manager, UI designer) and your interaction history. As the conversation progresses, the NPC's affection towards you will gradually increase, from "stranger" to "familiar", then to "friendly", "intimate", and even "close friend".

**The affection system is implemented in the back-end**. Each conversation adjusts the affection value based on the player's message content and sentiment analysis. Although the affection value is not directly displayed in the front-end game interface, all affection changes are recorded in detail in the back-end logs. You can view the affection changes for each conversation in the `backend/logs/dialogue_YYYY-MM-DD.log` file. The log file records detailed information for each conversation, including: current affection value, retrieved relevant memories, NPC's reply, affection change amount (+2.0, +3.0, etc.), reason for change (friendly greeting, normal communication, etc.), and sentiment analysis results (positive, neutral, etc.). This design allows developers to clearly track the relationship development between NPCs and players, and also provides a data foundation for adding affection UI to the front-end later.

All conversations are recorded in the back-end log files. You can view them in real-time with the following command:

```bash
# In the backend directory
python view_logs.py
```

This simple experience demonstrates the core features of AI Town. Next, we will dive into how to implement these features.

## 15.2 NPC Agent System

### 15.2.1 SimpleAgent Based on HelloAgents

In Cyber Town, each NPC is an independent agent. We use SimpleAgent from the HelloAgents framework to implement NPC intelligence. SimpleAgent is a lightweight agent implementation that encapsulates core functions such as LLM calls, message management, and tool calls.

Recall the SimpleAgent we learned in Chapter 7. Its core is a simple dialogue loop: receive user message, call LLM to generate reply, return result. In Cyber Town, we need to create a SimpleAgent instance for each NPC and configure unique system prompts for them, giving each NPC different personalities and role settings.

Let's see how to create an NPC Agent. First, we need to define the NPC's basic information, including ID, name, profession, and personality. Then, we build system prompts based on this information, letting the LLM play the role of this NPC. Finally, we create a SimpleAgent instance and configure the memory system.

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.memory import MemoryManager, WorkingMemory, EpisodicMemory

def create_npc_agent(npc_id: str, name: str, role: str, personality: str):
    """Create NPC Agent"""
    # Build system prompt
    system_prompt = f"""You are {name}, a {role}.
Your personality traits: {personality}

You work in the Datawhale office, working with colleagues to promote the development of the open source community.
Please have natural conversations with players based on your role and personality.
Remember your previous conversations to maintain dialogue coherence.
"""

    # Create LLM instance
    llm = HelloAgentsLLM()

    # Create memory manager
    memory_manager = MemoryManager(
        working_memory=WorkingMemory(capacity=10, ttl_minutes=120),
        episodic_memory=EpisodicMemory(
            db_path=f"memory_data/{npc_id}_episodic.db",
            collection_name=f"{npc_id}_memories"
        )
    )

    # Create Agent
    agent = SimpleAgent(
        name=name,
        llm=llm,
        system_prompt=system_prompt,
        memory_manager=memory_manager
    )

    return agent
```

This code demonstrates how to create an NPC Agent. The system prompt defines the NPC's identity and personality, and the memory manager allows the NPC to remember conversation history with players. WorkingMemory is short-term memory with a capacity of 10 messages and a retention time of 120 minutes. EpisodicMemory is long-term memory, using SQLite database and Qdrant vector database for storage, and can retrieve relevant historical conversations.

The workflow of NPC Agent is shown in Figure 15.5:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-5.png" alt="" width="85%"/>
  <p>Figure 15.5 NPC Agent Workflow</p>
</div>

### 15.2.2 NPC Role Settings and Prompt Design

A good NPC needs distinct personality and role settings. In Cyber Town, we designed three NPCs representing different professions and personalities.

**Zhang San - Python Engineer**

Zhang San is a senior Python engineer responsible for the core development of the HelloAgents framework. He has a rigorous personality, speaks directly, and likes to use technical terms. He has high requirements for code quality and often shares programming tips and best practices.

```python
npc_zhang = {
    "npc_id": "zhang_san",
    "name": "Zhang San",
    "role": "Python Engineer",
    "personality": "Rigorous, professional, likes to share technical knowledge. Speaks directly, focuses on code quality."
}
```

**Li Si - Product Manager**

Li Si is an experienced product manager responsible for product planning and user experience design of the HelloAgents framework. He has an outgoing personality, is good at communication, and can always think from the user's perspective. He likes to discuss product design and user needs, and often asks "why".

```python
npc_li = {
    "npc_id": "li_si",
    "name": "Li Si",
    "role": "Product Manager",
    "personality": "Outgoing, good at communication, focuses on user experience. Likes to think from the user's perspective."
}
```

**Wang Wu - UI Designer**

Wang Wu is a creative UI designer responsible for interface design and visual presentation of the HelloAgents framework. He has a gentle personality, unique aesthetics, and keen perception of color and layout. He likes to discuss design concepts and aesthetics, and often shares design inspiration.

```python
npc_wang = {
    "npc_id": "wang_wu",
    "name": "Wang Wu",
    "role": "UI Designer",
    "personality": "Gentle, creative, unique aesthetics. Focuses on visual presentation and user experience."
}
```

These three NPCs have distinct characteristics. Players can choose to interact with different NPCs based on their interests. Zhang San can teach you programming skills, Li Si can discuss product design with you, and Wang Wu can share design inspiration.

### 15.2.3 Memory System Integration

The memory system is the key to NPC intelligence. An NPC that can remember past conversations will make players feel more realistic and interesting. We use HelloAgents' `WorkingMemory` and `EpisodicMemory` to construct short-term and long-term memory.

Short-term memory stores recent conversation content with limited capacity and automatic cleanup over time. Its role is to maintain dialogue coherence, allowing NPCs to understand context. For example, when a player says "What color is it?", the NPC needs to find from short-term memory what "it" refers to.

Long-term memory stores all conversation history, using vector databases for semantic retrieval. When a player mentions a topic, the NPC can retrieve relevant historical conversations from long-term memory, recalling previously discussed content. For example, when a player says "Do you remember the project we discussed last time?", the NPC can find relevant conversation records from long-term memory.

The architecture of the memory system is shown in Figure 15.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-6.png" alt="" width="85%"/>
  <p>Figure 15.6 Memory System Architecture</p>
</div>

In actual use, the Agent first obtains recent conversations from short-term memory, then retrieves relevant historical conversations from long-term memory, sends this information together to the LLM, and generates more accurate and personalized replies.

```python
# Agent's dialogue processing flow
def process_dialogue(agent, player_message):
    # 1. Get recent conversations from short-term memory
    recent_messages = agent.memory_manager.working_memory.get_recent_messages(5)

    # 2. Retrieve relevant history from long-term memory
    relevant_memories = agent.memory_manager.episodic_memory.search(
        query=player_message,
        top_k=3
    )

    # 3. Build context
    context = {
        "recent": recent_messages,
        "relevant": relevant_memories
    }

    # 4. Call Agent to generate reply
    reply = agent.run(player_message, context=context)

    # 5. Save to memory system
    agent.memory_manager.add_interaction(player_message, reply)

    return reply
```

This process ensures that NPCs can remember interaction history with players and reflect it in conversations.

### 15.2.4 Batch Dialogue Generation: Light Load Mode

In actual operation, a problem was quickly discovered: when multiple players simultaneously converse with different NPCs, the back-end needs to concurrently process multiple LLM requests. Each request needs to call the API, which not only increases costs but may also cause request failures or delays due to concurrency limits.

To solve this problem, we designed a **batch dialogue generation system**. The core idea is: merge multiple NPC dialogue requests into one LLM call, letting the LLM generate all NPC replies at once. This is like a restaurant's "pre-made dishes" - prepared in batches in advance, used directly when needed, greatly reducing costs and latency.

The workflow of batch generation is shown in Figure 15.7:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-7.png" alt="" width="85%"/>
  <p>Figure 15.7 Batch Generation vs Traditional Mode</p>
</div>

The implementation of the batch generator is very clever. We build a special prompt requiring the LLM to generate all NPC dialogues at once and return them in JSON format. This way, one API call can obtain all NPC replies, reducing costs to 1/3 of the original and significantly reducing latency.

```python
class NPCBatchGenerator:
    """Generator for batch generating NPC dialogues"""

    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.npc_configs = NPC_ROLES  # All NPC configurations

    def generate_batch_dialogues(self, context: Optional[str] = None) -> Dict[str, str]:
        """Batch generate dialogues for all NPCs

        Args:
            context: Scene context (such as "morning work time", "lunch time", etc.)

        Returns:
            Dict[str, str]: Mapping from NPC names to dialogue content
        """
        # Build batch generation prompt
        prompt = self._build_batch_prompt(context)

        # One LLM call generates all dialogues
        response = self.llm.invoke([
            {"role": "system", "content": "You are a game NPC dialogue generator, skilled at creating natural and realistic office dialogues."},
            {"role": "user", "content": prompt}
        ])

        # Parse JSON response
        dialogues = json.loads(response)
        # Return format: {"Zhang San": "...", "Li Si": "...", "Wang Wu": "..."}

        return dialogues

    def _build_batch_prompt(self, context: Optional[str] = None) -> str:
        """Build batch generation prompt"""
        # Automatically infer scene based on time
        if context is None:
            context = self._get_current_context()

        # Build NPC descriptions
        npc_descriptions = []
        for name, cfg in self.npc_configs.items():
            desc = f"- {name}({cfg['title']}): {cfg['activity']} at {cfg['location']}, personality {cfg['personality']}"
            npc_descriptions.append(desc)

        npc_desc_text = "\n".join(npc_descriptions)

        prompt = f"""Please generate current dialogues or behavior descriptions for 3 NPCs in the Datawhale office.

【Scene】{context}

【NPC Information】
{npc_desc_text}

【Generation Requirements】
1. Generate 1 sentence for each NPC (20-40 characters)
2. Content should match role settings, current activities, and scene atmosphere
3. Can be self-talk, work status description, or simple thoughts
4. Should be natural and realistic, like real office colleagues
5. **Must strictly return in JSON format**

【Output Format】(strictly follow)
{{"Zhang San": "...", "Li Si": "...", "Wang Wu": "..."}}

【Example Output】
{{"Zhang San": "This bug is really annoying, been debugging for two hours...", "Li Si": "Hmm, the priority of this feature needs to be re-evaluated.", "Wang Wu": "The latte art on this coffee is really nice, inspiration is coming!"}}

Please generate (only return JSON, no other content):
"""
        return prompt
```

The key to this design is the construction of the prompt. We explicitly require the LLM to return JSON format and provide example output. The LLM will strictly generate replies according to this format, and we only need to parse the JSON to obtain all NPC dialogues.

Batch generation has an additional benefit: all NPC dialogues are generated in the same context, so they have a certain degree of correlation. For example, if Zhang San is debugging a bug, Li Si might mention helping to take a look; if Wang Wu is designing an interface, Zhang San might say he'll check the design draft later. This makes the atmosphere of the entire office more realistic and coherent.

Of course, batch generation also has some limitations. It is more suitable for generating NPC "background dialogues" or "self-talk" rather than direct interactions with players. For player-initiated conversations, we still use individual Agents to process them to ensure personalized and accurate replies. Batch generation is mainly used in the following scenarios:

1. **NPC background dialogues**: What NPCs are doing and saying when players enter the scene
2. **Timed updates**: Update NPC status and dialogues at regular intervals
3. **Scene atmosphere**: Generate different dialogues based on time (morning, noon, evening)
4. **Cost reduction**: Use batch generation to reduce API call frequency in high-concurrency scenarios

**Hybrid Mode: Batch Generation + Instant Response**

In actual implementation, we adopted a hybrid mode that combines batch generation and instant response. This design is very clever, ensuring both efficiency and interaction quality.

Specifically, the system periodically runs batch generation in the background, generating "background dialogues" for all NPCs in the current scene. These dialogues are cached, and when players approach NPCs but haven't initiated interaction yet, NPCs will display these background dialogues, such as "Debugging code...", "Reading product documentation...", etc. This makes NPCs appear "alive" rather than static models.

However, when a player presses the E key to initiate interaction, the system immediately switches to instant response mode. At this point, the back-end calls the NPC's dedicated Agent, generating personalized replies based on the player's specific message, historical memory, and affection level. This process is real-time, ensuring that NPC replies are highly relevant to player input.

```python
# Hybrid mode implementation in main.py
@app.post("/dialogue")
async def dialogue(request: DialogueRequest):
    """Handle player-NPC dialogue (instant response mode)"""
    npc_id = request.npc_id
    player_message = request.player_message
    player_name = request.player_name

    # Get NPC Agent (each NPC has an independent Agent)
    agent = npc_agents.get(npc_id)
    if not agent:
        raise HTTPException(status_code=404, detail="NPC not found")

    # Instantly generate personalized reply
    # Here we don't use batch generation, but call Agent's run method
    reply = agent.run(player_message)

    # Update affection
    affinity_change = relationship_manager.update_affinity(
        npc_id, player_name, player_message, reply
    )

    return {
        "npc_reply": reply,
        "affinity_score": affinity_change["score"],
        "affinity_level": affinity_change["level"]
    }

# Background task: periodically batch generate background dialogues
async def background_dialogue_update():
    """Background task: update NPC background dialogues every 5 minutes"""
    while True:
        try:
            # Use batch generator to generate background dialogues for all NPCs
            batch_generator = get_batch_generator()
            dialogues = batch_generator.generate_batch_dialogues()

            # Update to state manager
            for npc_name, dialogue in dialogues.items():
                state_manager.update_npc_background_dialogue(npc_name, dialogue)

            print(f"✅ Background dialogue update complete: {len(dialogues)} NPCs")
        except Exception as e:
            print(f"❌ Background dialogue update failed: {e}")

        # Wait 5 minutes
        await asyncio.sleep(300)
```

The advantages of this hybrid mode are very obvious:

1. **Cost reduction**: Background dialogues use batch generation, one call generates all NPC dialogues, low cost
2. **Quality assurance**: Player interactions use instant response, each reply is personalized, high quality
3. **Enhanced experience**: NPCs always have "background dialogues", appearing very lively; player interactions have accurate replies, good experience
4. **Flexible adjustment**: Can dynamically adjust batch generation frequency based on server load

Through the combination of batch generation and instant response, we implemented an NPC system that is both efficient and intelligent. Under normal circumstances, players don't feel any difference, but back-end costs and performance are significantly optimized. This design approach can also be applied to other scenarios requiring a large number of AI calls.

## 15.3 Affection System Design

### 15.3.1 Affection Level Classification

In Cyber Town, NPC attitudes towards players change with interactions. We designed a five-level affection system, from stranger to close friend, with each level having different score ranges and corresponding behavioral performances.

The core idea of the affection system is: by quantifying the relationship between NPCs and players, make NPC replies more realistic and layered. When players first enter the game, all NPCs have a stranger attitude towards players, with replies being polite but distant. As conversations progress, if players behave friendly, NPC affection will gradually increase, and replies will become more cordial and detailed.

We divide affection into five levels, each corresponding to a score range, as shown in Figure 15.8:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-8.png" alt="" width="85%"/>
  <p>Figure 15.8 Affection Level Classification</p>
</div>

- **Stranger (0-20 points)**: NPC just met the player, attitude is polite but maintains distance. Replies are brief, won't actively share personal information.

- **Familiar (21-40 points)**: NPC starts to remember the player, willing to have simple exchanges. Replies become more natural, occasionally sharing some work-related information.

- **Friendly (41-60 points)**: NPC treats the player as a friend, willing to share more information. Replies are more detailed, will actively ask about the player's situation.

- **Intimate (61-80 points)**: NPC trusts the player very much, willing to share private topics. Replies are full of enthusiasm, will provide help and advice to the player.

- **Close Friend (81-100 points)**: NPC treats the player as the best friend, talks about everything. Replies are very cordial, will share inner thoughts and feelings.

This design allows players to clearly feel the change in their relationship with NPCs, and also provides a foundation for subsequent gameplay. For example, only after reaching a certain affection level will NPCs share certain special information or provide special tasks.

### 15.3.2 Affection Calculation Logic

Affection calculation needs to consider multiple factors. We can't simply add a fixed score for each conversation, which would make the system appear mechanical and unrealistic. A good affection system should be able to identify the player's attitude and dynamically adjust scores based on conversation content.

In Cyber Town, we use LLM to analyze conversation content, judging whether the player's attitude is friendly, neutral, or unfriendly. Then we adjust the affection score based on the judgment result. This process is automatic, players don't need to deliberately choose options, making interactions more natural.

The affection calculation process is shown in Figure 15.9:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-9.png" alt="" width="85%"/>
  <p>Figure 15.9 Affection Calculation Process</p>
</div>

```python
class RelationshipManager:
    """Affection manager"""

    def __init__(self):
        self.affinity_data = {}  # Store affection data
        self.llm = HelloAgentsLLM()  # For analyzing conversations

    def analyze_sentiment(self, player_message: str, npc_reply: str) -> int:
        """Analyze conversation sentiment, return affection change value"""
        prompt = f"""Analyze the player's attitude in the following conversation:
Player: {player_message}
NPC: {npc_reply}

Please judge if the player's attitude is:
1. Friendly (+5 points): Polite, enthusiastic, expressing thanks or agreement
2. Neutral (+2 points): Normal inquiry or statement
3. Unfriendly (-3 points): Rude, indifferent, critical or negative

Only return the number, no other content."""

        response = self.llm.think([{"role": "user", "content": prompt}])
        try:
            score_change = int(response.strip())
            return max(-3, min(5, score_change))  # Limit between -3 and 5
        except:
            return 2  # Default neutral

    def update_affinity(self, npc_id: str, player_name: str,
                       player_message: str, npc_reply: str) -> dict:
        """Update affection"""
        key = f"{npc_id}_{player_name}"

        # Get current affection
        if key not in self.affinity_data:
            self.affinity_data[key] = {
                "score": 0,
                "level": "Stranger",
                "interaction_count": 0
            }

        # Analyze conversation sentiment
        score_change = self.analyze_sentiment(player_message, npc_reply)

        # Update score
        current_score = self.affinity_data[key]["score"]
        new_score = max(0, min(100, current_score + score_change))

        # Update level
        level = self.get_affinity_level(new_score)

        # Update data
        self.affinity_data[key].update({
            "score": new_score,
            "level": level,
            "interaction_count": self.affinity_data[key]["interaction_count"] + 1
        })

        return self.affinity_data[key]

    def get_affinity_level(self, score: int) -> str:
        """Get affection level based on score"""
        if score <= 20:
            return "Stranger"
        elif score <= 40:
            return "Familiar"
        elif score <= 60:
            return "Friendly"
        elif score <= 80:
            return "Intimate"
        else:
            return "Close Friend"
```

This implementation uses LLM to analyze conversation content, automatically judging the player's attitude and adjusting affection. This design makes the affection system more intelligent and natural, players don't need to deliberately please NPCs, just communicate normally.

### 15.3.3 Affection Affects Dialogue

Affection is not just a number, it should truly affect NPC behavior. In Cyber Town, we modify NPC system prompts to let NPCs adjust reply styles based on current affection levels.

When affection is low, NPCs maintain a polite but distant attitude. When affection increases, NPCs become more enthusiastic and talkative. This change is achieved by dynamically adjusting system prompts.

```python
def create_npc_agent_with_affinity(npc_id: str, name: str, role: str,
                                   personality: str, affinity_level: str):
    """Create NPC Agent with affection"""

    # Adjust prompts based on affection level
    affinity_prompts = {
        "Stranger": "You just met this player, be polite but not overly enthusiastic. Keep replies brief and professional.",
        "Familiar": "You already know this player, can have normal exchanges. Replies should be natural and friendly.",
        "Friendly": "You treat this player as a friend, willing to share more information. Replies should be detailed and enthusiastic.",
        "Intimate": "You trust this player very much, can share private topics. Replies should be full of care.",
        "Close Friend": "You treat this player as your best friend, talk about everything. Replies should be cordial and sincere."
    }

    system_prompt = f"""You are {name}, a {role}.
Your personality traits: {personality}

Current relationship with player: {affinity_level}
{affinity_prompts.get(affinity_level, affinity_prompts["Stranger"])}

You work in the Datawhale office, working with colleagues to promote the development of the open source community.
Please reply naturally based on your role, personality, and relationship with the player.
"""

    # Create Agent
    llm = HelloAgentsLLM()
    agent = SimpleAgent(
        name=name,
        llm=llm,
        system_prompt=system_prompt
    )

    return agent
```

This design makes NPC behavior change dynamically with affection. Players can clearly feel that as interactions increase, NPC attitudes towards them are gradually changing, greatly enhancing the game's immersion and fun.

## 15.4 Back-End Service Implementation

### 15.4.1 FastAPI Application Structure

The back-end of Cyber Town is built using the FastAPI framework, responsible for handling requests from the Godot front-end, calling HelloAgents' NPC Agents, managing NPC state and affection, and recording logs. A clear application structure makes code easier to maintain and extend.

Our FastAPI application adopts a modular design, separating different functions into different files, as shown in Figure 15.10:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-10.png" alt="" width="85%"/>
  <p>Figure 15.10 Back-End Application Structure</p>
</div>

Let's start with `main.py`, the entry file for the FastAPI application:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from agents import NPCAgentManager
from relationship_manager import RelationshipManager
from state_manager import StateManager
from logger import DialogueLogger
from config import settings

# Create FastAPI application
app = FastAPI(
    title="Cyber Town Back-End Service",
    description="AI NPC dialogue system based on HelloAgents",
    version="1.0.0"
)

# Configure CORS, allow Godot front-end access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production environment should limit specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize各个managers
agent_manager = NPCAgentManager()
relationship_manager = RelationshipManager()
state_manager = StateManager()
dialogue_logger = DialogueLogger()

@app.on_event("startup")
async def startup_event():
    """Initialization on application startup"""
    print("=" * 60)
    print("🎮 Cyber Town back-end service starting...")
    print("=" * 60)

    # Initialize NPC Agents
    agent_manager.initialize_npcs()
    print("✅ NPC Agents initialized")

    # Initialize state manager
    state_manager.initialize_npcs()
    print("✅ State manager initialized")

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "running",
        "message": "Cyber Town back-end service is running",
        "version": "1.0.0",
        "npcs": state_manager.get_npc_count()
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
```

This main program file defines the basic structure of the FastAPI application, configures CORS middleware to allow cross-origin requests, and initializes各个managers on startup. Next we will implement specific API routes.

### 15.4.2 API Route Design

The back-end of Cyber Town needs to provide several core API endpoints to handle requests from the Godot front-end. We add these routes to `main.py`.

**Get NPC Status**

This API returns the current status of all NPCs, including location, whether busy, etc.:

```python
from models import NPCStatusResponse

@app.get("/npcs/status", response_model=NPCStatusResponse)
async def get_npc_status():
    """Get status of all NPCs"""
    npcs = state_manager.get_all_npc_states()
    return {"npcs": npcs}

@app.get("/npcs/{npc_id}/status")
async def get_single_npc_status(npc_id: str):
    """Get status of a single NPC"""
    npc = state_manager.get_npc_state(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} does not exist")
    return npc
```

**Dialogue Interface**

This is the most core API, handling player-NPC conversations:

```python
from models import DialogueRequest, DialogueResponse

@app.post("/dialogue", response_model=DialogueResponse)
async def dialogue(request: DialogueRequest):
    """Handle player-NPC dialogue"""
    # 1. Verify NPC exists
    if not agent_manager.has_npc(request.npc_id):
        raise HTTPException(status_code=404, detail=f"NPC {request.npc_id} does not exist")

    # 2. Check if NPC is busy
    if state_manager.is_npc_busy(request.npc_id):
        raise HTTPException(status_code=409, detail=f"NPC {request.npc_id} is talking with another player")

    # 3. Mark NPC as busy
    state_manager.set_npc_busy(request.npc_id, True)

    try:
        # 4. Get current affection
        affinity_info = relationship_manager.get_affinity(
            request.npc_id,
            request.player_name
        )

        # 5. Call Agent to generate reply
        agent = agent_manager.get_agent(request.npc_id, affinity_info["level"])
        reply = agent.run(request.player_message)

        # 6. Update affection
        new_affinity = relationship_manager.update_affinity(
            request.npc_id,
            request.player_name,
            request.player_message,
            reply
        )

        # 7. Record log
        dialogue_logger.log_dialogue(
            npc_id=request.npc_id,
            player_name=request.player_name,
            player_message=request.player_message,
            npc_reply=reply,
            affinity_info=new_affinity
        )

        # 8. Return reply
        return DialogueResponse(
            npc_reply=reply,
            affinity_level=new_affinity["level"],
            affinity_score=new_affinity["score"]
        )

    except Exception as e:
        dialogue_logger.log_error(f"Dialogue processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dialogue processing failed: {str(e)}")

    finally:
        # 9. Release NPC status
        state_manager.set_npc_busy(request.npc_id, False)
```

**Affection Query**

This API allows querying player-NPC affection:

```python
from models import AffinityInfo

@app.get("/affinity/{npc_id}/{player_name}", response_model=AffinityInfo)
async def get_affinity(npc_id: str, player_name: str):
    """Get player-NPC affection"""
    if not agent_manager.has_npc(npc_id):
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} does not exist")

    affinity = relationship_manager.get_affinity(npc_id, player_name)
    return affinity
```

The API route call flow is shown in Figure 15.11:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-11.png" alt="" width="85%"/>
  <p>Figure 15.11 API Call Flow</p>
</div>

### 15.4.3 State Management and Logging System

**State Manager**

The state manager is responsible for tracking the current state of each NPC, including location, whether busy, current action, etc. This is important for preventing concurrency issues, such as avoiding an NPC talking with multiple players simultaneously.

```python
# state_manager.py
from typing import Dict, List, Optional
from datetime import datetime

class StateManager:
    """NPC state manager"""

    def __init__(self):
        self.npc_states: Dict[str, dict] = {}

    def initialize_npcs(self):
        """Initialize NPC states"""
        npcs = [
            {
                "npc_id": "zhang_san",
                "name": "Zhang San",
                "role": "Python Engineer",
                "position": {"x": 300, "y": 200}
            },
            {
                "npc_id": "li_si",
                "name": "Li Si",
                "role": "Product Manager",
                "position": {"x": 500, "y": 200}
            },
            {
                "npc_id": "wang_wu",
                "name": "Wang Wu",
                "role": "UI Designer",
                "position": {"x": 700, "y": 200}
            }
        ]

        for npc in npcs:
            self.npc_states[npc["npc_id"]] = {
                **npc,
                "is_busy": False,
                "current_action": "idle",
                "last_interaction": None
            }

    def get_npc_state(self, npc_id: str) -> Optional[dict]:
        """Get NPC state"""
        return self.npc_states.get(npc_id)

    def get_all_npc_states(self) -> List[dict]:
        """Get all NPC states"""
        return list(self.npc_states.values())

    def is_npc_busy(self, npc_id: str) -> bool:
        """Check if NPC is busy"""
        npc = self.npc_states.get(npc_id)
        return npc["is_busy"] if npc else False

    def set_npc_busy(self, npc_id: str, busy: bool):
        """Set NPC busy status"""
        if npc_id in self.npc_states:
            self.npc_states[npc_id]["is_busy"] = busy
            if busy:
                self.npc_states[npc_id]["last_interaction"] = datetime.now().isoformat()

    def get_npc_count(self) -> int:
        """Get NPC count"""
        return len(self.npc_states)
```

**Logging System**

The logging system implements dual output: console and file. This makes it convenient to view in real-time and save historical records.

```python
# logger.py
import logging
from datetime import datetime
from pathlib import Path

class DialogueLogger:
    """Dialogue logger"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create log file name (by date)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"dialogue_{today}.log"

        # Configure logging
        self.logger = logging.getLogger("DialogueLogger")
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def log_dialogue(self, npc_id: str, player_name: str,
                    player_message: str, npc_reply: str,
                    affinity_info: dict):
        """Log dialogue"""
        log_message = f"""
{'='*60}
NPC: {npc_id}
Player: {player_name}
Player message: {player_message}
NPC reply: {npc_reply}
Affection: {affinity_info['level']} ({affinity_info['score']}/100)
Interaction count: {affinity_info['interaction_count']}
{'='*60}
"""
        self.logger.info(log_message)

    def log_error(self, error_message: str):
        """Log error"""
        self.logger.error(error_message)
```

This logging system displays dialogue content in real-time on the console while saving it to files. Each day's logs are saved in separate files for easy subsequent analysis.

### 15.4.4 Understanding Godot's Scene System

Before starting to build game scenes, we need to first understand Godot's core concepts - Scene and Node. This is the biggest difference between Godot and other game engines, and also one of its most powerful features.

**What is a Node?**

Nodes are the most basic building blocks in Godot. You can think of nodes as Lego bricks, each node has a specific function. For example, Sprite2D nodes are used to display images, AudioStreamPlayer nodes are used to play audio, and CharacterBody2D nodes are used to handle character physics movement. Godot provides hundreds of different types of nodes, each focusing on doing one thing well.

Nodes can form parent-child relationships, forming a tree structure. Parent nodes can affect child nodes, for example, moving a parent node will simultaneously move all child nodes, hiding a parent node will simultaneously hide all child nodes. This hierarchical relationship allows us to easily organize and manage complex game objects.

**What is a Scene?**

A scene is a collection of nodes, saved in a .tscn file. You can think of a scene as a "prefab". For example, we can create a "player" scene containing all related nodes such as character sprites, collision bodies, sound effects, etc. Then use this scene multiple times in the game, each use will create an independent instance.

The power of scenes lies in their reusability and modularity. We can instantiate one scene within another scene, forming nested structures. For example, the main scene can contain player scenes, multiple NPC scenes, and UI scenes. Modifying the NPC scene will automatically affect all NPC instances, greatly simplifying development and maintenance.

**A Simple Example**

Let's use a simple example to understand scenes and nodes. Suppose we want to create a "player" scene:

```
Player (CharacterBody2D)  ← Root node, responsible for physics movement
├─ AnimatedSprite2D       ← Child node, displays character animation
├─ CollisionShape2D       ← Child node, defines collision shape
└─ Camera2D               ← Child node, camera follows player
```

This scene contains 4 nodes forming a tree structure. CharacterBody2D is the root node, the other three are its child nodes. We can add scripts to each node to control its behavior, or add a script to the root node to coordinate all child nodes.

When we instantiate this Player scene in the main scene, Godot creates a copy of this entire node tree. We can create multiple player instances, each instance is independent with its own position, state, and behavior.

**Advantages of Scene Instantiation**

In Cyber Town, we have three NPCs: Zhang San, Li Si, and Wang Wu. Without using the scene system, we would need to create nodes, set properties, and write scripts for each NPC separately, leading to a lot of repetitive work. Using the scene system, we only need to create a generic NPC scene, then instantiate it three times, setting different names and role information through script parameters.

The benefit of this design is: if we want to add a new feature to all NPCs (such as displaying dialogue bubbles above their heads), we only need to modify the NPC scene, and all instances will automatically get this feature.

## 15.5 Godot Game Scene Construction

**Why Choose Godot as the Game Engine?**

Among many game engines, we chose Godot 4.5 as the front-end engine, mainly based on the following considerations:

(1) **Godot has natural advantages in 2D game development**. Cyber Town is a top-down 2D pixel-style game. Godot's 2D engine is very mature, providing node types specifically designed for 2D games such as TileMap, AnimatedSprite2D, CharacterBody2D, etc. Development efficiency is much higher than engines like Unity. Godot's Scene System allows us to encapsulate elements like players, NPCs, and UI into independent scenes, then instantiate them in the main scene. This component-based design is very suitable for our needs.

(2) **Godot is completely open source and free**. Godot uses the MIT license, with no royalty fees or revenue sharing, which is very friendly for teaching projects and open source projects. You can freely modify the engine source code and commercialize games without worrying about licensing issues. In contrast, although Unity is powerful, it introduced a runtime fee policy in 2024, causing widespread controversy in the developer community.

(3) **Godot has an extremely low learning cost**. Godot uses GDScript as its main scripting language, a dynamically typed language similar to Python with concise and easy-to-understand syntax and a very gentle learning curve. For readers already familiar with Python, learning GDScript has almost no barrier - variable declarations, function definitions, control flow, and other syntax are highly similar to Python. You can even start writing game scripts within a few hours. Godot's node tree structure is also very intuitive, you can visually see the scene's hierarchical relationships in the editor, which is very friendly for beginners.

(4) **Godot integrates very simply with Python back-ends**. Godot has a built-in HTTPRequest node that can easily communicate with FastAPI back-ends via HTTP. We only need to create an API client script encapsulating all API calls to invoke back-end AI capabilities in the game. This front-end and back-end separation architecture allows us to independently develop and test game logic and AI logic, greatly improving development efficiency.

Of course, Godot also has some limitations. For example, Godot's 3D capabilities still lag behind Unreal Engine and Unity. If you want to develop large-scale 3D games, you may need to consider other engines. But for 2D games, indie games, and teaching projects, Godot is an excellent choice.

### 15.5.1 Scene Design and Resource Organization

After understanding Godot's scene system, let's look at Cyber Town's scene design. The entire game consists of four core scenes: Main (main scene), Player (player), NPC (non-player character), and DialogueUI (dialogue interface). Each scene is an independent module that can be edited and tested separately, then combined to form a complete game.

Cyber Town's scene organization adopts a modular design. We first create three basic scenes: Player (player), NPC (non-player character), and DialogueUI (dialogue interface). Then in Main (main scene), we instantiate and combine these scenes. It's particularly worth noting that the three NPCs (Zhang San, Li Si, Wang Wu) are all instances of the same NPC scene, just with different role information set through script parameters.

Let's first look at the structure of the four core scenes, as shown in Figure 15.12:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-12.png" alt="" width="85%"/>
  <p>Figure 15.12 Four Core Scenes of Cyber Town</p>
</div>

This diagram shows four independent scenes and their internal structures. **Scene 1 (Main)** is the main scene, containing background image (Sprite2D), player instance, NPCs organization node (with three NPC instances below), dialogue interface instance, walls organization node, and background music. Note that Player, NPC_Zhang, NPC_Li, NPC_Wang, and DialogueUI here are scene instances, not ordinary nodes. **Scene 2 (Player)** defines the player character structure, including animation, collision, camera, and two sound effect nodes. **Scene 3 (NPC)** is a generic template - Zhang San, Li Si, and Wang Wu are all instances of this scene, containing collision, animation, interaction area, and two labels. **Scene 4 (DialogueUI)** is a CanvasLayer node containing Panel and various UI elements.

The scene instantiation process can be understood this way: We created the NPC.tscn scene file in the Godot editor, defining the NPC's node structure. Then in the Main scene, we "instantiated" this NPC scene three times, creating three independent copies named NPC_Zhang, NPC_Li, and NPC_Wang respectively. Each copy has its own position and state, but they share the same node structure. If we modify NPC.tscn, such as adding a new sound effect node to the NPC, all three instances will automatically get this sound effect.

The steps to create these scenes in Godot are as follows:

1. **Create Player scene**: Create new scene, select CharacterBody2D as root node, add AnimatedSprite2D, CollisionShape2D, Camera2D, InteractSound, and RunningSound child nodes, save as Player.tscn.

2. **Create NPC scene**: Create new scene, select CharacterBody2D as root node, add CollisionShape2D, AnimatedSprite2D, InteractionArea (Area2D with CollisionShape2D below), NameLabel, and DialogueLabel child nodes, save as NPC.tscn.

3. **Create DialogueUI scene**: Create new scene, select CanvasLayer as root node, add Panel child node, under Panel add NPCName, NPCTitle, DialogueText (RichTextLabel), PlayerInput (LineEdit), SendButton, and CloseButton, save as DialogueUI.tscn.

4. **Create Main scene**: Create new scene, select Node2D as root node, add Background (Sprite2D) as background image, under Background add whale decoration, then instantiate Player scene, create NPCs node and instantiate NPC scene three times below it, instantiate DialogueUI scene, create Walls node for organizing wall collisions, finally add AudioStreamPlayer to play background music.

The advantages of this scene organization method are: each scene is independent and can be tested separately; NPCs use instances of the same scene, modifying once affects all NPCs; scenes communicate through signals with low coupling, easy to maintain and extend.

### 15.5.2 Player Control Implementation

The player character is one of the most important elements in the game. We need to implement WASD movement control, animation switching, collision detection, interaction with NPCs, and sound effects system.

The player scene structure includes: a CharacterBody2D as the root node, responsible for physics movement and collision; an AnimatedSprite2D displaying character animation; a CollisionShape2D defining collision shape; a Camera2D following the player; two AudioStreamPlayers playing interaction sound effects and walking sound effects respectively.

The player control script `player.gd` implements movement, interaction, and sound effect logic:

```python
extends CharacterBody2D

# Movement speed
@export var speed: float = 200.0

# Currently interactable NPC
var nearby_npc: Node = null

# Interaction state (disable movement during interaction)
var is_interacting: bool = false

# Node references
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var camera: Camera2D = $Camera2D

# Sound effect references
@onready var interact_sound: AudioStreamPlayer = null
@onready var running_sound: AudioStreamPlayer = null

# Walking sound effect state
var is_playing_running_sound: bool = false

func _ready():
    # Add to player group (important! NPCs need this group to identify player)
    add_to_group("player")

    # Get sound effect nodes (optional, won't error if doesn't exist)
    interact_sound = get_node_or_null("InteractSound")
    running_sound = get_node_or_null("RunningSound")

    # Enable camera
    camera.enabled = true

    # Play default animation
    if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
        animated_sprite.play("idle")

func _physics_process(_delta: float):
    # If interacting, disable movement
    if is_interacting:
        velocity = Vector2.ZERO
        move_and_slide()
        # Play idle animation
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")
        # Stop walking sound effect
        stop_running_sound()
        return

    # Get input direction
    var input_direction = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

    # Set velocity
    velocity = input_direction * speed

    # Move
    move_and_slide()

    # Update animation and direction
    update_animation(input_direction)

    # Update walking sound effect
    update_running_sound(input_direction)

func update_animation(direction: Vector2):
    """Update character animation (supports 4 directions)"""
    if animated_sprite.sprite_frames == null:
        return

    # Play animation based on movement direction
    if direction.length() > 0:
        # Moving - determine main direction
        if abs(direction.x) > abs(direction.y):
            # Left-right movement
            if direction.x > 0:
                # Right
                if animated_sprite.sprite_frames.has_animation("walk_right"):
                    animated_sprite.play("walk_right")
                    animated_sprite.flip_h = false
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = false
            else:
                # Left
                if animated_sprite.sprite_frames.has_animation("walk_left"):
                    animated_sprite.play("walk_left")
                    animated_sprite.flip_h = false
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = true
        else:
            # Up-down movement
            if direction.y > 0:
                # Down
                if animated_sprite.sprite_frames.has_animation("walk_down"):
                    animated_sprite.play("walk_down")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
            else:
                # Up
                if animated_sprite.sprite_frames.has_animation("walk_up"):
                    animated_sprite.play("walk_up")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
    else:
        # Idle
        if animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func _input(event: InputEvent):
    # Press E key to interact with NPC
    if event is InputEventKey:
        if event.pressed and not event.echo:
            if event.keycode == KEY_E or event.keycode == KEY_ENTER:
                if nearby_npc != null:
                    interact_with_npc()

func interact_with_npc():
    """Interact with nearby NPC"""
    if nearby_npc != null:
        # Play interaction sound effect
        if interact_sound:
            interact_sound.play()

        # Send signal to dialogue system
        get_tree().call_group("dialogue_system", "start_dialogue", nearby_npc.npc_name)

func set_nearby_npc(npc: Node):
    """Set nearby NPC"""
    nearby_npc = npc

func set_interacting(interacting: bool):
    """Set interaction state"""
    is_interacting = interacting
    if interacting:
        # Stop walking sound effect
        stop_running_sound()

func update_running_sound(direction: Vector2):
    """Update walking sound effect"""
    if running_sound == null:
        return

    # If moving
    if direction.length() > 0:
        # If sound effect not playing yet, start playing
        if not is_playing_running_sound:
            running_sound.play()
            is_playing_running_sound = true
    else:
        # If stopped moving, stop sound effect
        stop_running_sound()

func stop_running_sound():
    """Stop walking sound effect"""
    if running_sound and is_playing_running_sound:
        running_sound.stop()
        is_playing_running_sound = false
```

This script implements complete player control. Players use WASD keys (or arrow keys) to move, and the character plays corresponding 4-direction animations (walk_up/down/left/right) based on movement direction. When the player approaches an NPC, the NPC calls `set_nearby_npc()` to set itself as an interactable object, and the player can press the E key to trigger interaction. During interaction, sound effects play, and `call_group()` notifies the dialogue system to start conversation. During dialogue, `set_interacting(true)` disables player movement, which is restored after dialogue ends. Walking sound effects automatically play when the player moves and automatically stop when stopped.

### 15.5.3 NPC Behavior and Interaction

NPCs need to implement three core functions: randomly patrol and wander in the scene, respond to player interactions, and display dialogue bubbles. We use Area2D to detect whether the player is near the NPC. When the player enters the interaction range, the player is notified, and pressing the E key starts the conversation.

The NPC scene structure includes: CharacterBody2D as root node; CollisionShape2D defines NPC collision shape; AnimatedSprite2D displays NPC animation; InteractionArea (Area2D) detects player entering interaction range, with CollisionShape2D below defining interaction range; NameLabel displays NPC name; DialogueLabel displays dialogue bubble.

The NPC script `npc.gd` implements patrol, interaction, and dialogue bubble logic:

```python
extends CharacterBody2D

# NPC information
@export var npc_name: String = "Zhang San"
@export var npc_title: String = "Python Engineer"

# NPC appearance configuration
@export var sprite_frames: SpriteFrames = null  # Custom sprite frame resource

# NPC movement configuration
@export var move_speed: float = 50.0  # Movement speed
@export var wander_enabled: bool = true  # Whether to enable patrol
@export var wander_range: float = 200.0  # Patrol range
@export var wander_interval_min: float = 3.0  # Minimum patrol interval (seconds)
@export var wander_interval_max: float = 8.0  # Maximum patrol interval (seconds)

# Current dialogue content (obtained from back-end)
var current_dialogue: String = ""

# Node references
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var interaction_area: Area2D = $InteractionArea
@onready var name_label: Label = $NameLabel
@onready var dialogue_label: Label = $DialogueLabel

# Player reference
var player: Node = null

# Patrol-related variables
var wander_target: Vector2 = Vector2.ZERO  # Patrol target position
var wander_timer: float = 0.0  # Patrol timer
var is_wandering: bool = false  # Whether currently patrolling
var is_interacting: bool = false  # Whether currently interacting with player
var spawn_position: Vector2 = Vector2.ZERO  # Spawn position

func _ready():
    # Add to npcs group
    add_to_group("npcs")

    # Set NPC name
    name_label.text = npc_name

    # Connect interaction area signals
    interaction_area.body_entered.connect(_on_body_entered)
    interaction_area.body_exited.connect(_on_body_exited)

    # Initialize dialogue label
    dialogue_label.text = ""
    dialogue_label.visible = false

    # Set custom sprite frames (if any)
    if sprite_frames != null:
        animated_sprite.sprite_frames = sprite_frames

    # Play default animation
    if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
        animated_sprite.play("idle")

    # Record spawn position
    spawn_position = global_position

    # Initialize patrol timer
    if wander_enabled:
        wander_timer = randf_range(wander_interval_min, wander_interval_max)
        choose_new_wander_target()

func _on_body_entered(body: Node2D):
    """Player enters interaction range"""
    if body.is_in_group("player"):
        player = body

        if player.has_method("set_nearby_npc"):
            player.set_nearby_npc(self)

func _on_body_exited(body: Node2D):
    """Player leaves interaction range"""
    if body.is_in_group("player"):
        if player != null and player.has_method("set_nearby_npc"):
            player.set_nearby_npc(null)
        player = null

func update_dialogue(dialogue: String):
    """Update NPC dialogue content"""
    current_dialogue = dialogue
    dialogue_label.text = dialogue
    dialogue_label.visible = true

    # Hide dialogue after 10 seconds
    await get_tree().create_timer(10.0).timeout
    dialogue_label.visible = false

func _physics_process(delta: float):
    """Physics update - handle movement"""
    # If interacting with player, stop movement
    if is_interacting:
        velocity = Vector2.ZERO
        move_and_slide()
        # Play idle animation
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")
        return

    # If patrol not enabled, don't move
    if not wander_enabled:
        return

    # Update patrol timer
    wander_timer -= delta

    # If timer ends, choose new target and start moving
    if wander_timer <= 0:
        choose_new_wander_target()
        wander_timer = randf_range(wander_interval_min, wander_interval_max)

    # If patrolling, move to target
    if is_wandering:
        # Check if reached target
        if global_position.distance_to(wander_target) < 10:
            # Reached target, stop movement
            is_wandering = false
            velocity = Vector2.ZERO
            move_and_slide()
            # Play idle animation
            if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
                animated_sprite.play("idle")
        else:
            # Continue moving to target
            var direction = (wander_target - global_position).normalized()
            velocity = direction * move_speed
            move_and_slide()
            # Update animation
            update_animation(direction)
    else:
        # Stop movement
        velocity = Vector2.ZERO
        move_and_slide()
        # Play idle animation
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func choose_new_wander_target():
    """Choose new patrol target"""
    # Randomly choose a point near spawn position
    var offset = Vector2(
        randf_range(-wander_range, wander_range),
        randf_range(-wander_range, wander_range)
    )
    wander_target = spawn_position + offset
    is_wandering = true

func update_animation(direction: Vector2):
    """Update animation"""
    if animated_sprite.sprite_frames == null:
        return

    if direction.length() > 0:
        # Movement animation
        if abs(direction.x) > abs(direction.y):
            # Left-right movement
            if direction.x > 0:
                if animated_sprite.sprite_frames.has_animation("walk_right"):
                    animated_sprite.play("walk_right")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = false
            else:
                if animated_sprite.sprite_frames.has_animation("walk_left"):
                    animated_sprite.play("walk_left")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = true
        else:
            # Up-down movement
            if direction.y > 0:
                if animated_sprite.sprite_frames.has_animation("walk_down"):
                    animated_sprite.play("walk_down")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
            else:
                if animated_sprite.sprite_frames.has_animation("walk_up"):
                    animated_sprite.play("walk_up")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
    else:
        # Idle animation
        if animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func set_interacting(interacting: bool):
    """Set interaction state"""
    is_interacting = interacting
```

This script implements complete NPC behavior. NPCs randomly patrol within the `wander_range` around their spawn position, choosing a new target point and moving there every `wander_interval_min` to `wander_interval_max` seconds. During movement, 4-direction animations (walk_up/down/left/right) play, and upon reaching the target, they stop and play the idle animation. When a player enters the InteractionArea, the NPC calls the player's `set_nearby_npc(self)` method, setting itself as an interactable object. After the player presses the E key, the dialogue system calls the NPC's `set_interacting(true)` method, and the NPC stops moving. After dialogue ends, `set_interacting(false)` is called, and the NPC resumes patrol. The main scene periodically calls the `update_dialogue()` method to update the NPC's dialogue bubble, displaying autonomous dialogue content between NPCs.

## 15.6 Front-End and Back-End Communication Implementation

### 15.6.1 API Client Encapsulation

The Godot front-end needs to communicate with the FastAPI back-end via HTTP. We create an API client script `api_client.gd`, encapsulating all API calls, and set it as an AutoLoad (auto-load) singleton so other scripts can conveniently use it.

The API client uses Godot's HTTPRequest node to send HTTP requests. HTTPRequest is an asynchronous node that doesn't block the game after sending requests, but notifies request completion through signals. This ensures game fluidity - even with high network latency, there's no stuttering. We use the signal mechanism to notify other scripts of API responses rather than using await, allowing multiple scripts to simultaneously listen for the same API response.

```python
# api_client.gd
extends Node

# Signal definitions
signal chat_response_received(npc_name: String, message: String)
signal chat_error(error_message: String)
signal npc_status_received(dialogues: Dictionary)
signal npc_list_received(npcs: Array)

# HTTP request nodes
var http_chat: HTTPRequest
var http_status: HTTPRequest
var http_npcs: HTTPRequest

func _ready():
    # Create HTTP request nodes
    http_chat = HTTPRequest.new()
    http_status = HTTPRequest.new()
    http_npcs = HTTPRequest.new()

    add_child(http_chat)
    add_child(http_status)
    add_child(http_npcs)

    # Connect signals
    http_chat.request_completed.connect(_on_chat_request_completed)
    http_status.request_completed.connect(_on_status_request_completed)
    http_npcs.request_completed.connect(_on_npcs_request_completed)

# ==================== Chat API ====================
func send_chat(npc_name: String, message: String) -> void:
    """Send chat request"""
    var data = {
        "npc_name": npc_name,
        "message": message
    }

    var json_string = JSON.stringify(data)
    var headers = ["Content-Type: application/json"]

    var error = http_chat.request(
        Config.API_CHAT,
        headers,
        HTTPClient.METHOD_POST,
        json_string
    )

    if error != OK:
        print("[ERROR] Failed to send chat request: ", error)
        chat_error.emit("Network request failed")

func _on_chat_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Handle chat response"""
    if response_code != 200:
        print("[ERROR] Chat request failed: HTTP ", response_code)
        chat_error.emit("Server error: " + str(response_code))
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Failed to parse response")
        chat_error.emit("Response parsing failed")
        return

    var response = json.data

    if response.has("success") and response["success"]:
        var npc_name = response["npc_name"]
        var msg = response["message"]
        print("[INFO] Received NPC reply: ", npc_name, " -> ", msg)
        chat_response_received.emit(npc_name, msg)
    else:
        chat_error.emit("Chat failed")

# ==================== NPC Status API ====================
func get_npc_status() -> void:
    """Get NPC status"""
    # Check if request is being processed
    if http_status.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
        print("[WARN] NPC status request is being processed, skipping this request")
        return

    var error = http_status.request(Config.API_NPC_STATUS)

    if error != OK:
        print("[ERROR] Failed to get NPC status: ", error)

func _on_status_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Handle NPC status response"""
    if response_code != 200:
        print("[ERROR] NPC status request failed: HTTP ", response_code)
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Failed to parse NPC status")
        return

    var response = json.data

    if response.has("dialogues"):
        var dialogues = response["dialogues"]
        print("[INFO] Received NPC status update: ", dialogues.size(), " NPCs")
        npc_status_received.emit(dialogues)

# ==================== NPC List API ====================
func get_npc_list() -> void:
    """Get NPC list"""
    var error = http_npcs.request(Config.API_NPCS)

    if error != OK:
        print("[ERROR] Failed to get NPC list: ", error)

func _on_npcs_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Handle NPC list response"""
    if response_code != 200:
        print("[ERROR] NPC list request failed: HTTP ", response_code)
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Failed to parse NPC list")
        return

    var response = json.data

    if response.has("npcs"):
        var npcs = response["npcs"]
        print("[INFO] Received NPC list: ", npcs.size(), " NPCs")
        npc_list_received.emit(npcs)
```

This API client encapsulates three core functions: send chat request (`send_chat`), get NPC status (`get_npc_status`), and get NPC list (`get_npc_list`). All HTTP requests are asynchronous, notifying response results through signals. We created independent HTTPRequest nodes for each API, allowing multiple requests to be sent simultaneously without interfering with each other. API URLs are obtained from the Config singleton for convenient unified management. The dialogue system listens to the `chat_response_received` signal to receive NPC replies, and the main scene listens to the `npc_status_received` signal to update NPC dialogue bubbles.

### 15.6.2 Dialogue UI Implementation

The dialogue UI is the interface for player-NPC interaction. We need to design a simple and beautiful dialogue box containing NPC name, title, dialogue content display, input box, and buttons.

The dialogue UI structure is shown in Figure 15.13:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-13.png" alt="" width="85%"/>
  <p>Figure 15.13 Dialogue UI Structure</p>
</div>

The dialogue UI design is very simple. DialogueUI is a CanvasLayer node, meaning it will always display on top of the game screen and won't be obscured by other game objects. Panel is the dialogue box background, anchored at the bottom of the screen. Under Panel are 6 UI elements placed directly: NPCName displays the NPC's name, NPCTitle displays the title, DialogueText uses RichTextLabel to display dialogue content (supports rich text format), PlayerInput is a LineEdit for player input, and SendButton and CloseButton are used to send messages and close the dialogue box respectively.

The dialogue UI script `dialogue_ui.gd` implements the dialogue interface logic:

```python
# dialogue_ui.gd
extends CanvasLayer

# UI node references
@onready var panel = $Panel
@onready var npc_name_label = $Panel/NPCName
@onready var npc_title_label = $Panel/NPCTitle
@onready var dialogue_text = $Panel/DialogueText
@onready var input_field = $Panel/PlayerInput
@onready var send_button = $Panel/SendButton
@onready var close_button = $Panel/CloseButton

# API client
var api_client: Node = null

# Current NPC in dialogue
var current_npc_name: String = ""

func _ready():
    # Hide dialogue box on initialization
    visible = false

    # Connect button signals
    send_button.pressed.connect(_on_send_button_pressed)
    close_button.pressed.connect(_on_close_button_pressed)
    input_field.text_submitted.connect(_on_text_submitted)

    # Get API client
    api_client = get_node_or_null("/root/APIClient")

func start_dialogue(npc_name: String):
    """Start dialogue with NPC"""
    current_npc_name = npc_name

    # Set NPC information
    npc_name_label.text = npc_name
    npc_title_label.text = get_npc_title(npc_name)

    # Clear dialogue content
    dialogue_text.clear()
    dialogue_text.append_text("[color=gray]Conversation with " + npc_name + " started...[/color]\n")

    # Clear input field
    input_field.text = ""

    # Show dialogue box
    show_dialogue()

    # Focus input field
    input_field.grab_focus()

func show_dialogue():
    """Show dialogue box"""
    visible = true

    # Notify player to enter interaction state (disable movement)
    var player = get_tree().get_first_node_in_group("player")
    if player and player.has_method("set_interacting"):
        player.set_interacting(true)

func hide_dialogue():
    """Hide dialogue box"""
    visible = false
    current_npc_name = ""

    # Notify player to exit interaction state (enable movement)
    var player = get_tree().get_first_node_in_group("player")
    if player and player.has_method("set_interacting"):
        player.set_interacting(false)

func _on_send_button_pressed():
    """Send button clicked"""
    send_message()

func _on_close_button_pressed():
    """Close button clicked"""
    hide_dialogue()

func _on_text_submitted(_text: String):
    """Input field enter pressed"""
    send_message()

func send_message():
    """Send message"""
    var message = input_field.text.strip_edges()

    if message.is_empty():
        return

    if current_npc_name.is_empty():
        return

    # Display player message
    dialogue_text.append_text("\n[color=cyan]Player:[/color] " + message + "\n")

    # Clear input field
    input_field.text = ""

    # Disable input
    input_field.editable = false
    send_button.disabled = true

    # Send API request
    if api_client:
        api_client.send_chat_request(current_npc_name, message)

func on_chat_response_received(npc_name: String, response: String):
    """Received NPC reply"""
    if npc_name == current_npc_name:
        # Display NPC reply
        dialogue_text.append_text("[color=yellow]" + npc_name + ":[/color] " + response + "\n")

        # Enable input
        input_field.editable = true
        send_button.disabled = false
        input_field.grab_focus()

func get_npc_title(npc_name: String) -> String:
    """Get NPC title"""
    var titles = {
        "Zhang San": "Python Engineer",
        "Li Si": "Product Manager",
        "Wang Wu": "UI Designer"
    }
    return titles.get(npc_name, "")
```

This dialogue UI implements complete dialogue functionality. Players can input and send messages, and the UI uses RichTextLabel's append_text method to display dialogue content, supporting rich text format (colors, bold, etc.). All API calls are asynchronous, disabling the input box while waiting for responses to prevent duplicate sends. When the dialogue box is displayed, it notifies the player to enter interaction state, disabling movement, and restores movement when closed.

### 15.6.3 Main Scene Integration

Finally, we need to integrate all functions in the main scene: player control, NPC interaction, dialogue UI, and NPC status updates. The main scene script `main.gd` coordinates these components and periodically obtains NPC status from the back-end to update NPC dialogue bubbles.

```python
# main.gd
extends Node2D

# NPC node references
@onready var npc_zhang: Node2D = $NPCs/NPC_Zhang
@onready var npc_li: Node2D = $NPCs/NPC_Li
@onready var npc_wang: Node2D = $NPCs/NPC_Wang

# API client
var api_client: Node = null

# NPC status update timer
var status_update_timer: float = 0.0

func _ready():
    print("[INFO] Main scene initialization")

    # Get API client
    api_client = get_node_or_null("/root/APIClient")
    if api_client:
        api_client.npc_status_received.connect(_on_npc_status_received)

        # Immediately get NPC status once
        api_client.get_npc_status()
    else:
        print("[ERROR] API client not found")

func _process(delta: float):
    # Periodically update NPC status
    status_update_timer += delta
    if status_update_timer >= Config.NPC_STATUS_UPDATE_INTERVAL:
        status_update_timer = 0.0
        if api_client:
            api_client.get_npc_status()

func _on_npc_status_received(dialogues: Dictionary):
    """Received NPC status update"""
    print("[INFO] Update NPC status: ", dialogues)

    # Update each NPC's dialogue
    for npc_name in dialogues:
        var dialogue = dialogues[npc_name]
        update_npc_dialogue(npc_name, dialogue)

func update_npc_dialogue(npc_name: String, dialogue: String):
    """Update specified NPC's dialogue"""
    var npc_node = get_npc_node(npc_name)
    if npc_node and npc_node.has_method("update_dialogue"):
        npc_node.update_dialogue(dialogue)

func get_npc_node(npc_name: String) -> Node2D:
    """Get NPC node by name"""
    match npc_name:
        "Zhang San":
            return npc_zhang
        "Li Si":
            return npc_li
        "Wang Wu":
            return npc_wang
        _:
            return null
```

The core function of the main scene script is to periodically obtain NPC status from the back-end. In `_ready()`, we get a reference to the APIClient singleton and connect the `npc_status_received` signal. Then we immediately call `get_npc_status()` to get NPC status once. In `_process()`, we use a timer to call `get_npc_status()` every `Config.NPC_STATUS_UPDATE_INTERVAL` seconds (default 30 seconds). When NPC status updates are received, the `_on_npc_status_received()` callback function traverses all NPCs and calls their `update_dialogue()` method to update dialogue bubbles. This way, even if the player doesn't interact with NPCs, they can still see autonomous dialogue between NPCs.

The complete front-end and back-end communication process is shown in Figure 15.14:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-14.png" alt="" width="85%"/>
  <p>Figure 15.14 Complete Front-End and Back-End Communication Process</p>
</div>

At this point, all front-end and back-end communication functions have been implemented. Players can move freely in the game, interact with NPCs, and have natural language conversations. Meanwhile, the main scene periodically obtains NPC status from the back-end, updates NPC dialogue bubbles, and displays autonomous dialogue between NPCs. The entire system uses a signal mechanism for communication, with loose coupling between components, making it easy to maintain and extend.

## 15.7 Summary and Outlook

### 15.7.1 Chapter Review

In this chapter, we completed a full AI town project - Cyber Town. This project combines the HelloAgents framework with the Godot game engine to create a vibrant virtual world. Let's review the core content we learned.

**Technical Architecture Design**

We adopted a separated architecture of game engine + back-end service, separating front-end rendering, back-end logic, and AI intelligence into different layers. Godot handles game graphics and player interaction, FastAPI handles API services and state management, and HelloAgents handles NPC intelligence and memory systems. This layered design allows each part to be developed and tested independently, and also provides a good foundation for future expansion.

**NPC Agent System**

We used HelloAgents' SimpleAgent to create independent agents for each NPC. Each NPC has its own role setting, personality traits, and memory system. Through carefully designed system prompts, we made Zhang San a rigorous Python engineer, Li Si a product manager good at communication, and Wang Wu a creative UI designer. These NPCs can not only understand player dialogue but also respond according to their role characteristics.

**Memory and Affection System**

We implemented a two-layer memory system: short-term memory maintains dialogue coherence, and long-term memory stores all interaction history. Through semantic retrieval in vector databases, NPCs can recall previously discussed topics. The affection system allows NPCs' attitudes toward players to change with interaction, from stranger to close friend, with different behavioral expressions at each level. These designs make NPCs appear more realistic and interesting.

**Game Scene Construction**

We used Godot to create a pixel-style office scene, implementing player control, NPC wandering, interaction detection, and dialogue UI. Through the modular design of the scene system, we can easily add new NPCs, new scenes, and new functions. GDScript's concise syntax makes game logic implementation intuitive and efficient.

**Front-End and Back-End Communication**

We used HTTP REST API to implement communication between the Godot front-end and FastAPI back-end. Through asynchronous requests and signal systems, we ensured game fluidity - even with high network latency, player experience is not affected. The API client encapsulation allows other scripts to conveniently call back-end services, and the dialogue UI implementation allows players to naturally communicate with NPCs.

The project's technology stack is shown in Figure 15.15:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-15.png" alt="" width="85%"/>
  <p>Figure 15.15 Cyber Town Technology Stack</p>
</div>

### 15.7.2 Extension Directions

Cyber Town is just a starting point - there are many directions for extension. These extensions can not only enhance game fun but also explore more possibilities for AI technology in games.

**(1) Multiplayer Online Support**

Currently, Cyber Town is a single-player game, but we can extend it to a multiplayer online game. Multiple players can simultaneously enter the same office and interact with NPCs and other players. This requires introducing WebSocket for real-time communication and databases to persist player data and NPC states. NPCs can remember interactions with different players and maintain independent affection levels for each player.

**(2) Quest System**

We can design a quest system for NPCs. When a player's affection with an NPC reaches a certain level, the NPC will provide special quests. For example, Zhang San might ask the player to help debug code, Li Si might ask the player to collect user feedback, and Wang Wu might ask the player to evaluate design proposals. Completing quests can earn rewards and further increase affection.

**(3) NPC-to-NPC Interaction**

Currently, NPCs only interact with players, but we can enable NPCs to interact with each other. Zhang San can discuss product requirements with Li Si, Li Si can discuss interface design with Wang Wu, and Wang Wu can discuss technical implementation with Zhang San. These interactions can occur automatically in the background, and players can observe dialogue between NPCs, making the entire world appear more lively.

**(4) Emotion System**

In addition to affection, we can add a more complex emotion system for NPCs. NPCs can have different emotional states such as happy, sad, angry, and excited, which affect NPC reply style and behavior. For example, when an NPC is in a good mood, they'll be more willing to share information; when in a bad mood, they might be rather cold.

**(5) Dynamic Event System**

We can design dynamic events to make the game world richer. For example, regularly hold team meetings where all NPCs and players gather to discuss project progress; or hold birthday parties celebrating an NPC's birthday; or emergency tasks requiring everyone's collaboration. These events can increase game variety and fun.

**(6) Larger World**

Currently, Cyber Town has only one office scene, but we can expand to a larger world. We can add different scenes like cafes, libraries, and parks, each with different NPCs and interaction methods. Players can move between different scenes and explore a broader virtual world.

**(7) Personalized Learning**

NPCs can learn each player's preferences and habits. For example, if a player frequently discusses Python with Zhang San, the NPC will remember the player is interested in programming and will proactively share related content in the future. If a player likes playing games at night, the NPC will remember this time habit and be more active at night.

### 15.7.3 Reflection and Outlook

Cyber Town demonstrates the enormous potential of AI technology in games. NPCs in traditional games are limited by preset dialogue trees and scripts, while AI NPCs can understand and generate natural language, having real conversations with players. This not only enhances game immersion but also brings new possibilities to game design.

However, AI NPCs also face some challenges. First is the cost issue - each conversation requires calling the LLM API, which incurs certain fees. For large multiplayer online games, this cost could be very high. Second is the latency issue - LLM inference takes time, and if network latency is high, players might need to wait several seconds to see NPC replies. Finally, there's the content control issue - LLM-generated content may not be fully controllable, requiring well-designed prompts and content filtering mechanisms.

Despite these challenges, the future of AI NPCs remains full of promise. As LLM technology develops, inference speed will become faster and costs will become lower. Localized small LLMs are also developing rapidly - in the future, they may be able to run directly on players' devices, requiring no network requests at all. The combination of AI technology and games will bring players unprecedented experiences.

In Part 5's graduation project chapter, we will learn how to construct general agents using single agents and multi-agents - this will be your creative time, so stay tuned!
