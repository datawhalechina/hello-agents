<div align="right">
  English | <a href="./第二章 智能体发展史.md">中文</a>
</div>

# Chapter 2: History of Agents

To deeply understand why modern agents present their current form and the origins of their core design philosophies, this chapter will trace back through history: starting from the classical era of artificial intelligence, exploring how the earliest "intelligence" was defined within rule systems of logic and symbols; then witnessing the major shift from single, centralized intelligence models to distributed, collaborative intelligence thinking; and finally understanding how the "learning" paradigm completely transformed the way agents acquire capabilities, giving birth to the modern agents we see today.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-00.png" alt="Figure description" width="90%"/>
  <p>Figure 2.1 The evolutionary ladder of AI agents</p>
</div>

As shown in Figure 2.1, **the emergence of each new paradigm is to solve the core "pain points" or fundamental limitations of the previous generation paradigm.** While new solutions bring capability leaps, they also introduce new "limitations" that are difficult to overcome at the time, which in turn lay the groundwork for the birth of the next generation paradigm. Understanding this "problem-driven" iterative process helps us more profoundly grasp the deep reasons and historical inevitability behind modern agent technology choices.

## 2.1 Early Agents Based on Symbols and Logic

Early explorations in the field of artificial intelligence were deeply influenced by mathematical logic and fundamental principles of computer science. In that era, researchers generally held a belief: human intelligence, especially logical reasoning ability, could be captured and reproduced by formalized symbolic systems. This core idea gave birth to the first important paradigm of artificial intelligence—Symbolicism, also known as "Logic AI" or "Traditional AI."

In the view of symbolicism, the core of intelligent behavior is operating on symbols based on a set of explicit rules. Therefore, an agent can be viewed as a physical symbol system: it represents the external world through internal symbols and plans actions through logical reasoning. The "wisdom" of agents in this era came entirely from knowledge bases and reasoning rules pre-coded by designers, rather than acquired through autonomous learning.

### 2.1.1 Physical Symbol System Hypothesis

The theoretical foundation of the symbolicism era was the **Physical Symbol System Hypothesis (PSSH)**<sup>[1]</sup>, jointly proposed by **Allen Newell** and **Herbert A. Simon** in 1976. These two Turing Award winners provided theoretical guidance and criteria for implementing general artificial intelligence on computers through this hypothesis.

The hypothesis contains two core assertions:

1. **Sufficiency Assertion**: Any physical symbol system has sufficient means to produce general intelligent behavior.
2. **Necessity Assertion**: Any system capable of exhibiting general intelligent behavior must essentially be a physical symbol system.

A physical symbol system here refers to a system that can exist in the physical world, composed of a set of distinguishable symbols and a series of processes that operate on these symbols, with constituent elements as shown in Figure 2.2. These symbols can be combined into more complex structures (such as expressions), while processes can create, modify, copy, and destroy these symbol structures.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-0.png" alt="Figure description" width="90%"/>
  <p>Figure 2.2 Constituent elements of a physical symbol system</p>
</div>

In short, PSSH boldly declared: **The essence of intelligence is the computation and processing of symbols.**

This hypothesis had far-reaching influence. It transformed the study of the vague and complex philosophical problem of human mind into a concrete problem that could be engineered and implemented on computers. It instilled strong confidence in early artificial intelligence researchers that as long as we could find the right way to represent knowledge and design effective reasoning algorithms, we could definitely create machine intelligence comparable to humans. Almost all research in the symbolicism era, from expert systems to automated planning, was conducted under the guidance of this hypothesis.

### 2.1.2 Expert Systems

Under the direct influence of the physical symbol system hypothesis, **Expert Systems** became the most important and successful application achievement of the symbolicism era. The core goal of expert systems was to simulate the ability of human experts to solve problems in specific domains. By encoding expert knowledge and experience into computer programs, they could provide conclusions or recommendations comparable to or even surpassing human experts when facing similar problems.

A typical expert system usually consists of several core components including a knowledge base, inference engine, and user interface, with a general architecture as shown in Figure 2.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-1.png" alt="Figure description" width="90%"/>
  <p>Figure 2.3 General architecture of expert systems</p>
</div>

This architecture clearly embodies the design philosophy of separating knowledge from reasoning, an important characteristic of symbolicism AI.

**Knowledge Base and Inference Engine**

The "intelligence" of expert systems mainly comes from its two core components: the knowledge base and the inference engine.

- **Knowledge Base**: This is the knowledge storage center of the expert system, used to store domain expert knowledge and experience. **Knowledge Representation** is key to building a knowledge base. In expert systems, the most commonly used knowledge representation method is **Production Rules**, i.e., a series of conditional statements in "IF-THEN" form. For example: IF patient has fever symptoms AND cough THEN may have respiratory infection. These rules associate specific situations (IF part, conditions) with corresponding conclusions or actions (THEN part, conclusions). A complex expert system may contain hundreds or thousands of such rules, collectively forming a vast knowledge network.
- **Inference Engine**: The inference engine is the core computational engine of the expert system. It is a general program whose task is to find and apply relevant rules in the knowledge base based on facts provided by users, thereby deriving new conclusions. The inference engine mainly works in two ways:
  - **Forward Chaining**: Starting from known facts, continuously matching the IF parts of rules, triggering THEN part conclusions, and adding new conclusions to the fact base until finally deriving the goal or no new rules can be matched. This is a "data-driven" reasoning approach.
  - **Backward Chaining**: Starting from a hypothetical goal (such as "does the patient have pneumonia"), finding rules that can derive that goal, then taking the IF part of that rule as a new sub-goal, recursing in this way until all sub-goals can be proven by known facts. This is a "goal-driven" reasoning approach.

**Application Case and Analysis: MYCIN System**

MYCIN is one of the most famous and influential expert systems in history, developed by Stanford University in the 1970s<sup>[2]</sup>. It was designed to assist doctors in diagnosing bacterial blood infections and recommending appropriate antibiotic treatment plans.

- **Working Principle**: MYCIN collected patient symptoms, medical history, and test results through question-and-answer interactions with doctors. Its knowledge base contained about 600 "IF-THEN" rules provided by medical experts. The inference engine mainly worked in backward chaining: starting from the highest goal of "determining the pathogen," it backward-derived what evidence and conditions were needed, then asked doctors questions to obtain this information. Its simplified workflow is shown in Figure 2.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-2.png" alt="Figure description" width="90%"/>
  <p>Figure 2.4 Schematic diagram of MYCIN backward chaining reasoning process</p>
</div>

- **Uncertainty Handling**: Medical diagnosis is full of uncertainty. An important innovation of MYCIN was introducing the concept of **Certainty Factor (CF)**, using a numerical value between -1 and 1 to represent the credibility of a conclusion. This enabled the system to handle uncertain, ambiguous medical knowledge and provide diagnostic results with credibility assessments, which was closer to the real world than simple Boolean logic.
- **Achievements and Significance**: In an evaluation, MYCIN's performance in blood infection diagnosis exceeded that of non-specialist doctors and even reached the level of human experts. Its success eloquently proved the validity of the physical symbol system hypothesis: through careful knowledge engineering and symbolic reasoning, machines could indeed exhibit excellent "intelligence" in highly complex professional domains. MYCIN was not only a milestone in the development history of expert systems but also paved the way for subsequent commercial applications of artificial intelligence in various vertical domains.

### 2.1.3 SHRDLU

If expert systems demonstrated the "depth" of symbolic AI in professional domains, then the SHRDLU project<sup>[3]</sup> developed by **Terry Winograd** from 1968-1970 achieved a revolutionary breakthrough in "breadth." As shown in Figure 2.5, SHRDLU aimed to build a comprehensive intelligent agent that could interact fluently with humans through natural language in the micro-environment of the "blocks world." The "blocks world" is a simulated three-dimensional virtual space containing blocks of different shapes, colors, and sizes, as well as a virtual robotic arm that can grasp and move them. Users issue commands or ask questions to SHRDLU in natural language, and SHRDLU executes actions in the virtual world or provides text responses.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-3.png" alt="Figure description" width="90%"/>
  <p>Figure 2.5 SHRDLU's "blocks world" interaction interface</p>
</div>

SHRDLU attracted widespread attention at the time mainly because it was the first to integrate multiple independent artificial intelligence modules (such as language parsing, planning, memory) into a unified system and make them work collaboratively:

- **Natural Language Understanding**: SHRDLU could parse structurally complex and ambiguous English sentences. It could not only understand direct commands (such as `Pick up a big red block.`) but also handle more complex instructions, such as:
  - Reference resolution: `Find a block which is taller than the one you are holding and put it into the box.` In this instruction, the system needs to understand that `the one you are holding` refers to the object currently grasped by the robotic arm.
  - Contextual memory: Users could say `Grasp the pyramid.`, then ask `What does the box contain?`, and the system could answer by connecting the context.
- **Planning and Action**: After understanding instructions, SHRDLU could autonomously plan a series of necessary actions to complete tasks. For example, if the instruction was "put the blue block on the red block," and there was already another green block on the red block, the system would plan the action sequence of "first move the green block away, then put the blue block on."
- **Memory and Q&A**: SHRDLU had memory about its environment and its own behavior. Users could ask questions about this, such as:
  - Inquiring about world state: `Is there a large block behind a pyramid?`
  - Inquiring about behavior history: `Did you touch any pyramid before you put the green one on the little cube?`
  - Inquiring about behavior motivation: `Why did you pick up the red block?` SHRDLU could answer: `BECAUSE YOU ASKED ME TO.`

SHRDLU's historical status and influence are mainly reflected in three aspects:

- **Paradigm of Comprehensive Intelligence**: Before SHRDLU, AI research mostly focused on single functions. It was the first to integrate multiple AI modules such as language understanding, reasoning planning, and action memory into a unified system. Its "perceive-think-act" closed-loop design laid the foundation for modern agent research.
- **Popularization of Micro-World Research Methods**: Its success proved the feasibility of exploring and verifying basic principles of complex agents in a simplified environment with clear rules, a method that profoundly influenced subsequent robotics and AI planning research.
- **Optimism and Reflection Triggered**: SHRDLU's success sparked early optimistic expectations for AGI, but its capabilities were strictly limited to the blocks world. This limitation triggered long-term speculation in the AI field about the difference between "symbol processing" and "true understanding," revealing deep challenges on the path to general intelligence.

### 2.1.4 Fundamental Challenges Facing Symbolicism

Despite significant achievements in early projects, starting from the 1980s, symbolic AI encountered fundamental difficulties inherent in its methodology when moving from "micro-worlds" to the open, complex real world. These difficulties can mainly be summarized into two major categories:

**(1) Common-sense Knowledge and Knowledge Acquisition Bottleneck**

The "intelligence" of symbolic agents depends entirely on the quality and completeness of their knowledge bases. However, how to build a knowledge base that can support real-world interaction has proven to be an extremely arduous task, mainly reflected in two aspects:

- **Knowledge Acquisition Bottleneck**: The knowledge of expert systems needs to be constructed by human experts and knowledge engineers through tedious processes of interviews, refinement, and encoding. This process is costly, time-consuming, and difficult to scale. More importantly, much of human expert knowledge is implicit and intuitive, difficult to be clearly expressed as "IF-THEN" rules. Attempting to manually symbolize all knowledge of the entire world is considered an almost impossible task.
- **Common-sense Problem**: Human behavior relies on a vast background of common sense (for example, "water is wet," "ropes can pull but not push"), but symbolic systems know nothing about this unless explicitly encoded. Establishing a complete knowledge base for broad, vague common sense remains a major challenge to this day. The Cyc project<sup>[4]</sup>, after decades of effort, still has very limited results and applications.

**(2) Frame Problem and System Brittleness**

In addition to knowledge-level challenges, symbolicism also encountered logical dilemmas when dealing with a dynamically changing world.

- **Frame Problem**: In a dynamic world, how to efficiently determine what things have not changed after an agent executes an action is a logical puzzle<sup>[5]</sup>. Explicitly declaring all invariant states for each action is computationally infeasible, yet humans can effortlessly ignore irrelevant changes.
- **Brittleness**: Symbolic systems rely entirely on preset rules, making their behavior very "brittle." Once encountering any minor change or new situation outside the rules, the system may completely fail, unable to adapt flexibly like humans. SHRDLU's success was precisely because it operated in a closed world with complete rules, while the real world is full of exceptions.

## 2.2 Building Rule-Based Chatbots

After exploring the theoretical challenges of symbolicism, in this section we will intuitively experience how rule-based systems work through a specific programming practice. We will attempt to reproduce ELIZA, an extremely influential early chatbot in the history of artificial intelligence.

### 2.2.1 ELIZA's Design Philosophy

ELIZA was a computer program released in 1966 by MIT computer scientist **Joseph Weizenbaum**<sup>[6]</sup>, one of the famous early attempts in the field of natural language processing. ELIZA was not a single program but a framework that could execute different "scripts." Among them, the most widely known and successful script was "DOCTOR," which imitated a Rogerian non-directive psychotherapist.

ELIZA's working method was extremely clever: it never directly answered questions or provided information but identified keywords in user input, then applied a set of preset transformation rules to convert user statements into open-ended questions. For example, when a user said "I am sad about my boyfriend," ELIZA might identify the keyword "I am sad about..." and apply a rule to generate the response: "Why are you sad about your boyfriend?"

Weizenbaum's design philosophy was not to create an agent that could truly "understand" human emotions; on the contrary, he wanted to prove that through some simple sentence transformation techniques, machines could create an illusion of "intelligence" and "empathy" without understanding the conversation content at all. However, to his surprise, many people who interacted with ELIZA (including his secretary) developed emotional dependence on it, deeply believing it could understand them.

The practical goal of this section is to reproduce ELIZA's core mechanism to deeply understand the advantages and fundamental limitations of this rule-driven approach.

### 2.2.2 Pattern Matching and Text Substitution

ELIZA's algorithm flow is based on **Pattern Matching and Text Substitution**, which can be clearly decomposed into the following four steps:

1. **Keyword Identification and Ranking:** The rule base sets a priority for each keyword (such as `mother`, `dreamed`, `depressed`). When input contains multiple keywords, the program selects the rule corresponding to the keyword with the highest priority for processing.
2. **Decomposition Rules:** After finding a keyword, the program uses decomposition rules with wildcards (`*`) to capture the rest of the sentence.
   1. **Rule Example**: `* my *`
   2. **User Input**: `"My mother is afraid of me"`
   3. **Capture Result**: `["", "mother is afraid of me"]`
3. **Reassembly Rules:** The program selects one from a set of reassembly rules associated with the decomposition rule to generate a response (usually randomly selected to increase diversity), and optionally uses the content captured in the previous step.
   1. **Rule Example**: `"Tell me more about your family."`
   2. **Generated Output**: `"Tell me more about your family."`
4. **Pronoun Conversion:** Before reassembly, the program performs simple pronoun conversion (such as `I` → `you`, `my` → `your`) to maintain conversation coherence.

The entire workflow can be represented by a simple pseudocode idea:

```Python
FUNCTION generate_response(user_input):
    // 1. Split user input into words
    words = SPLIT(user_input)

    // 2. Find the highest priority keyword rule
    best_rule = FIND_BEST_RULE(words)
    IF best_rule is NULL:
        RETURN a_generic_response() // For example: "Please go on."

    // 3. Use rule to decompose user input
    decomposed_parts = DECOMPOSE(user_input, best_rule.decomposition_pattern)
    IF decomposition_failed:
        RETURN a_generic_response()

    // 4. Perform pronoun conversion on decomposed parts
    transformed_parts = TRANSFORM_PRONOUNS(decomposed_parts)

    // 5. Use reassembly rules to generate response
    response = REASSEMBLE(transformed_parts, best_rule.reassembly_patterns)

    RETURN response
```

Through this mechanism, ELIZA successfully simplified the complex natural language understanding problem into an operable, rule-based pattern matching game.

### 2.2.3 Implementation of Core Logic

Now, we will transform the technical principles described in the previous section into a simple, runnable Python function. The following code implements a mini version of ELIZA, which contains a small set of rules but is sufficient to demonstrate its core working mechanism.

```Python
import re
import random

# Define rule base: pattern (regular expression) -> response template list
rules = {
    r'I need (.*)': [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "Are you sure you need {0}?"
    ],
    r'Why don\'t you (.*)\?': [
        "Do you really think I don't {0}?",
        "Perhaps eventually I will {0}.",
        "Do you really want me to {0}?"
    ],
    r'Why can\'t I (.*)\?': [
        "Do you think you should be able to {0}?",
        "If you could {0}, what would you do?",
        "I don't know -- why can't you {0}?"
    ],
    r'I am (.*)': [
        "Did you come to me because you are {0}?",
        "How long have you been {0}?",
        "How do you feel about being {0}?"
    ],
    r'.* mother .*': [
        "Tell me more about your mother.",
        "What was your relationship with your mother like?",
        "How do you feel about your mother?"
    ],
    r'.* father .*': [
        "Tell me more about your father.",
        "How did your father make you feel?",
        "What has your father taught you?"
    ],
    r'.*': [
        "Please tell me more.",
        "Let's change focus a bit... Tell me about your family.",
        "Can you elaborate on that?"
    ]
}

# Define pronoun conversion rules
pronoun_swap = {
    "i": "you", "you": "i", "me": "you", "my": "your",
    "am": "are", "are": "am", "was": "were", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "yours": "mine",
    "mine": "yours"
}

def swap_pronouns(phrase):
    """
    Perform first/second person conversion on pronouns in input phrase
    """
    words = phrase.lower().split()
    swapped_words = [pronoun_swap.get(word, word) for word in words]
    return " ".join(swapped_words)

def respond(user_input):
    """
    Generate response based on rule base
    """
    for pattern, responses in rules.items():
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            # Capture matched part
            captured_group = match.group(1) if match.groups() else ''
            # Perform pronoun conversion
            swapped_group = swap_pronouns(captured_group)
            # Randomly select one from templates and format
            response = random.choice(responses).format(swapped_group)
            return response
    # If no specific rule is matched, use the last wildcard rule
    return random.choice(rules[r'.*'])

# Main chat loop
if __name__ == '__main__':
    print("Therapist: Hello! How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Therapist: Goodbye. It was nice talking to you.")
            break
        response = respond(user_input)
        print(f"Therapist: {response}")

>>>
Therapist: Hello! How can I help you today?
You: I am feeling sad today.
Therapist: How long have you been feeling sad today?
You: I need some help with my project.
Therapist: Are you sure you need some help with your project?
You: My mother is not happy with my work.
Therapist: Tell me more about your mother.
You: quit
Therapist: Goodbye. It was nice talking to you.
```

Through the above programming practice, we can intuitively summarize the fundamental limitations of rule-driven systems, which are direct confirmations of the theoretical challenges of symbolicism discussed in Section `2.1.4`:

- **Lack of Semantic Understanding**: The system does not understand word meanings. For example, when faced with the input "I am **not** happy," it will still mechanically match the `I am (.*)` rule and generate a semantically incorrect response because it cannot understand the role of the negation word "not."
- **No Contextual Memory**: The system is **stateless**, with each response based only on the current single sentence input, unable to conduct coherent multi-turn conversations.
- **Rule Scalability Problem**: Attempting to add more rules leads to explosive growth in the rule base size, and conflict management and priority handling between rules become extremely complex, ultimately making the system difficult to maintain.

However, despite these obvious defects, ELIZA produced the famous "**ELIZA effect**" at the time, with many users believing it could understand them. This illusion of intelligence mainly stemmed from its clever conversation strategies (such as playing a passive questioner, using open-ended templates) and humans' innate emotional projection psychology.

ELIZA's practice clearly revealed the core contradiction of the symbolicism approach: the system's seemingly intelligent performance depends entirely on rules pre-coded by designers. However, facing the infinite possibilities of real-world language, this exhaustive method is destined to be unscalable. The system has no true understanding, only executing symbol operations, which is the root of its brittleness.

## 2.3 Marvin Minsky's Society of Mind

The exploration of symbolicism and ELIZA's practice jointly pointed to a problem: a single, centralized reasoning engine built through preset rules seems difficult to lead to true intelligence. No matter how large the rule base, the system always appears rigid and brittle when facing the ambiguity, complexity, and infinite changes of the real world. This dilemma prompted some top thinkers to reflect on the most fundamental design philosophy of artificial intelligence. Among them, **Marvin Minsky** did not continue trying to add more rules to a single reasoning core but proposed a revolutionary question in his book **"The Society of Mind"**<sup>[7]</sup>: "What magical trick makes us intelligent? The trick is that there is no trick. The power of intelligence stems from our vast diversity, not from any single, perfect principle."

### 2.3.1 Reflection on Single Holistic Intelligence Models

From the 1970s to the 1980s, the limitations of symbolicism became increasingly apparent. Although expert systems achieved success in highly vertical domains, they could not possess child-like common sense; although SHRDLU could perform excellently in a closed blocks world, it could not understand anything outside that world; although ELIZA could imitate conversation, it knew nothing about the conversation content itself. These systems all followed a top-down design approach: an omniscient central processor that processes information and makes decisions according to a unified set of logical rules.

Facing this universal failure, Minsky began to raise a series of fundamental questions:

- **What is "understanding"?** When we say we understand a story, is this a single ability? Or is it actually the result of dozens of different mental processes working together, such as visualization ability, logical reasoning ability, emotional resonance ability, and social relationship common sense?
- **What is "common sense"?** Is common sense a huge knowledge base containing millions of logical rules (as attempted by the Cyc project)? Or is it a distributed network woven from countless specific experiences and simple rule fragments?
- **How should agents be built?** Should we continue pursuing a perfect, unified logical system, or should we acknowledge that intelligence itself is an "imperfect" hodgepodge composed of many functionally different, even conflicting simple parts?

These questions directly addressed the core drawbacks of single holistic intelligence models. Such models attempt to solve all problems with a unified representation and reasoning mechanism, but this is far from how we observe natural intelligence (especially human intelligence) operating. Minsky believed that forcibly cramming diverse mental activities into a rigid logical framework was the root cause of early artificial intelligence research stagnation.

Based on this reflection, Minsky proposed a subversive conception: he no longer viewed the mind as a pyramid-like hierarchical structure but saw it as a flattened "society" full of interaction and collaboration.

### 2.3.2 Intelligence as Collaboration

In Minsky's theoretical framework, the definition of an agent differs from the modern agents we discussed in Chapter 1. Here, an agent refers to an extremely simple, specialized mental process that is itself "mindless." For example, a `LINE-FINDER` agent responsible for identifying lines, or a `GRASP` agent responsible for grasping.

These simple agents are organized to form more powerful **Agencies**. An agency is a group of agents working together to complete a more complex task. For example, a `BUILD` agency responsible for building blocks might be composed of multiple lower-level agents or agencies such as `SEE`, `FIND`, `GET`, and `PUT`. They influence each other through decentralized activation and inhibition signals, forming dynamic control flow.

**Emergence** is key to understanding the society of mind theory. Complex, purposeful intelligent behavior is not pre-planned by some high-level agent but spontaneously arises from local interactions among numerous simple bottom-level agents.

Let's use the classic "building a block tower" task as an example to illustrate this process, as shown in Figure 2.6. When a high-level goal (such as "I want to build a tower") appears, it activates a high-level agency called `BUILD-TOWER`.

1. The `BUILD-TOWER` agency doesn't know how to execute specific physical actions; its only role is to activate its subordinate agencies, such as `BUILDER`.
2. The `BUILDER` agency is also very simple; it might only contain loop logic: as long as the tower isn't finished, activate the `ADD-BLOCK` agency.
3. The `ADD-BLOCK` agency is responsible for coordinating more specific subtasks; it sequentially activates three sub-agencies: `FIND-BLOCK`, `GET-BLOCK`, and `PUT-ON-TOP`.
4. Each sub-agency is composed of even lower-level agents. For example, the `GET-BLOCK` agency activates the `SEE-SHAPE` agent in the visual system and the `REACH` and `GRASP` agents in the motor system.

In this process, no single agent or agency has a global plan for the entire task. `GRASP` is only responsible for grasping; it doesn't know what a tower is; `BUILDER` is only responsible for looping; it doesn't know how to control the arm. However, when this society composed of countless "mindless" agents interacts through simple activation and inhibition rules, a seemingly highly intelligent behavior—building a block tower—naturally emerges.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-4.png" alt="Figure description" width="90%"/>
  <p>Figure 2.6 Schematic diagram of the emergence mechanism of block tower building behavior in the "society of mind"</p>
</div>

### 2.3.3 Theoretical Inspiration for Multi-Agent Systems

The most far-reaching influence of the society of mind theory is that it provided an important conceptual foundation for **Distributed Artificial Intelligence (DAI)** and later **Multi-Agent Systems (MAS)**. It prompted researchers to think:

**If intelligence within a mind emerges through collaboration of numerous simple agents, then can more powerful "collective intelligence" also emerge through collaboration among multiple independent, physically separated computational entities (computers, robots)?**

The raising of this question directly shifted research focus from "how to build an omnipotent single agent" to "how to design an efficiently collaborating agent group." Specifically, the society of mind directly inspired MAS research in the following aspects:

- **Decentralized Control**: The core of the theory is that there is no central controller. This idea was completely inherited by the MAS field, and how to design coordination mechanisms and task allocation strategies without central nodes became one of the core research topics of MAS.
- **Emergent Computation**: Solutions to complex problems can spontaneously arise from simple local interaction rules. This inspired numerous emergence-based algorithms in MAS, such as ant colony algorithms and particle swarm optimization, for solving complex optimization and search problems.
- **Agent Sociality**: Minsky's theory emphasized interactions between agents (activation, inhibition). The MAS field further expanded this, systematically studying communication languages between agents (such as ACL), interaction protocols (such as contract nets), negotiation strategies, trust models, and even organizational structures, thereby constructing true computational societies.

It can be said that Minsky's "society of mind" theory provided an important analytical framework for AI researchers to understand the internal structure of "collective intelligence." It provided later researchers with a completely new perspective to explore complex systems composed of independent, autonomous, socially capable computational agents, formally opening the prelude to multi-agent system research.

## 2.4 Evolution of Learning Paradigms and Modern Agents

The "society of mind" theory discussed earlier pointed the way for collective intelligence and decentralized collaboration at the philosophical level, but the implementation path remained unclear. Meanwhile, the fundamental challenges exposed by symbolicism in dealing with real-world complexity also indicated that truly robust intelligence could not be built solely on pre-coded rules.

These two threads jointly pointed to a question: If intelligence cannot be completely designed, can it be learned?

This question opened the "learning" era of artificial intelligence. Its core goal was no longer to manually encode knowledge but to build systems that could automatically acquire knowledge and capabilities from experience and data. This section will trace the evolution of this paradigm: from the learning foundation laid by connectionism, to interactive learning achieved by reinforcement learning, to modern agents driven by large language models today.

### 2.4.1 From Symbols to Connections

As a direct response to the limitations of symbolicism, **Connectionism** re-emerged in the 1980s. Unlike symbolicism's top-down design philosophy relying on explicit logical rules, connectionism is a bottom-up approach inspired by mimicking the neural network structure of biological brains<sup>[8]</sup>. Its core ideas can be summarized as follows:

1. **Distributed Representation of Knowledge**: Knowledge is not stored in some knowledge base in the form of explicit symbols or rules but is stored in a distributed manner in the form of connection weights between numerous simple processing units (i.e., artificial neurons). The connection pattern of the entire network itself constitutes knowledge.
2. **Simple Processing Units**: Each neuron only performs very simple computations, such as receiving weighted inputs from other neurons, processing them through an activation function, and then outputting results to the next neuron.
3. **Adjusting Weights Through Learning**: The system's intelligence does not come from complex programs pre-written by designers but from the "learning" process. By being exposed to numerous samples, the system automatically and iteratively adjusts connection weights between neurons according to some learning algorithm (such as backpropagation), gradually making the entire network's output approach the desired target.

Under this paradigm, agents are no longer passive logical reasoning machines executing rules but adaptive systems capable of self-optimization through experience. As shown in Figure 2.7, this represents a fundamental shift in the core idea of building agents. Symbolicism attempted to explicitly encode human knowledge to machines, while connectionism attempted to create machines that could learn knowledge like humans.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-5.png" alt="Figure description" width="90%"/>
  <p>Figure 2.7 Comparison of symbolicism and connectionism paradigms</p>
</div>

The rise of connectionism, especially the success of deep learning in the 21st century, endowed agents with powerful perception and pattern recognition capabilities, enabling them to directly understand the world from raw data (such as images, sounds, text), which was unimaginable in the symbolicism era. However, how to enable agents to learn to make optimal sequential decisions in dynamic interactions with the environment required supplementation from another learning paradigm.

### 2.4.2 Agents Based on Reinforcement Learning

Connectionism mainly solved perception problems (for example, "What's in this picture?"), but the more core task of agents is decision-making (for example, "What should I do in this situation?"). **Reinforcement Learning (RL)** is precisely the learning paradigm focused on solving sequential decision problems. It does not directly learn from labeled static datasets but learns how to maximize its long-term benefits through direct interaction between agents and the environment, learning through "trial and error."

Taking AlphaGo as an example, its core self-play learning process is a classic embodiment of reinforcement learning<sup>[9]</sup>. In this process, AlphaGo (the agent) observes the current board layout (environment state) and decides where to place the next stone (action). After a game ends, based on the win-loss result, it receives a clear signal: winning is a positive reward, losing is a negative reward. Through millions of such self-play sessions, AlphaGo continuously adjusts its internal strategy, gradually learning which actions to choose in which board situations are most likely to lead to final victory. This process is completely autonomous, not relying on direct guidance from human game records.

This learning mechanism of optimizing one's own behavior through interaction with the environment and based on feedback signals is the core framework of reinforcement learning. Below we will detail its basic constituent elements and working mode.

The reinforcement learning framework can be described by several core elements:

- **Agent**: The learner and decision-maker. In AlphaGo's example, it's its decision-making program.
- **Environment**: Everything external to the agent, the object with which the agent interacts. For AlphaGo, it's the rules of Go and the opponent.
- **State (S)**: A specific description of the environment at a certain moment, the basis for the agent's decision-making. For example, the current positions of all stones on the board.
- **Action (A)**: Operations the agent can take based on the current state. For example, placing a stone at a legal position on the board.
- **Reward (R)**: A scalar signal fed back to the agent by the environment after the agent executes an action, used to evaluate the quality of that action in a specific state. For example, at the end of a game, victory receives a +1 reward, defeat receives a -1 reward.

Based on the above core elements, reinforcement learning agents continuously iterate in a "perceive-act-learn" closed loop, with their working mode shown in Figure 2.8.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-6.png" alt="Figure description" width="90%"/>
  <p>Figure 2.8 Core interaction loop of reinforcement learning</p>
</div>

The specific steps of this loop are as follows:

1. At time step t, the agent observes the current state $S_{t}$ of the environment.
2. Based on state $S_{t}$, the agent selects an action $A_{t}$ according to its internal **Policy (π)** and executes it. A policy is essentially a mapping from states to actions, defining the agent's behavior.
3. After receiving action $A_{t}$, the environment transitions to a new state $S_{t+1}$.
4. Simultaneously, the environment feeds back an immediate reward $R_{t+1}$ to the agent.
5. The agent uses this feedback (new state $S_{t+1}$ and reward $R_{t+1}$) to update and optimize its internal policy to make better decisions in the future. This update process is learning.

The agent's learning goal is not to maximize the immediate reward at a certain time step but to maximize the **Cumulative Reward** from the current moment to the future, also called **Return**. This means the agent needs to have "foresight"; sometimes to obtain greater future rewards, it needs to sacrifice current immediate rewards (for example, the "sacrifice" strategy in Go). Through continuous exploration, feedback collection, and policy optimization in the above loop, the agent can ultimately learn to make autonomous decisions and long-term planning in complex dynamic environments.

### 2.4.3 Pre-training Based on Large-Scale Data

Reinforcement learning endowed agents with the ability to learn decision-making strategies from interactions, but this typically requires massive task-specific interaction data, resulting in agents lacking prior knowledge at the beginning of learning and needing to build understanding of tasks from scratch. Whether it's the common sense that symbolicism attempted to manually encode or the background knowledge humans rely on when making decisions, both are missing in RL agents. How to enable agents to have broad understanding of the world before starting to learn specific tasks? The solution to this problem ultimately emerged in the field of **Natural Language Processing (NLP)**, with its core being **Pre-training** based on large-scale data.

**From Specific Tasks to General Models**

Before the emergence of the pre-training paradigm, traditional natural language processing models were typically trained from scratch independently for single specific tasks (such as sentiment analysis, machine translation) on specially annotated small to medium-scale datasets. This mode led to several problems: models had narrow knowledge scope, difficulty generalizing knowledge learned in one task to another, and each new task required substantial human effort for data annotation. The proposal of the Pre-training and Fine-tuning paradigm completely changed this situation. Its core idea is divided into two steps:

1. **Pre-training Phase**: First, train a super-large-scale neural network model on a general corpus containing internet-level massive text data through **Self-supervised Learning**. The goal of this phase is not to complete any specific task but to learn the inherent patterns, grammatical structures, factual knowledge, and contextual logic of language itself. The most common objective is "predicting the next word."
2. **Fine-tuning Phase**: After completing pre-training, this model has already learned rich knowledge related to the dataset. Subsequently, for specific downstream tasks, only a small amount of annotated data for that task is needed to fine-tune the model, allowing it to adapt to the corresponding task.

As shown in Figure 2.9, this intuitively demonstrates the complete process of pre-training and fine-tuning: general text data forms a foundation model through self-supervised learning, then fine-tuning with specific task data ultimately adapts to various downstream tasks.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-7.png" alt="Figure description" width="90%"/>
  <p>Figure 2.9 Schematic diagram of the "pre-training-fine-tuning" paradigm</p>
</div>

**Birth of Large Language Models and Emergent Abilities**

Through pre-training on trillions of texts, the neural network weights of large language models have actually constructed a highly compressed implicit model of world knowledge. It solves the most troublesome "knowledge acquisition bottleneck" problem of the symbolicism era in a completely new way. More surprisingly, when the model's scale (number of parameters, data volume, computation) crosses a certain threshold, they begin to exhibit unexpected **Emergent Abilities** that were not directly trained, such as:

- **In-context Learning**: Without adjusting model weights, just by providing **a few examples (Few-shot)** or even **zero examples (Zero-shot)** in the input, the model can understand and complete new tasks.
- **Chain-of-Thought** Reasoning: By guiding the model to output step-by-step reasoning processes before answering complex questions, its accuracy on logic, arithmetic, and common-sense reasoning tasks can be significantly improved.

The emergence of these abilities marks that LLMs are no longer just language models; they have evolved into components playing dual roles as both massive knowledge bases and general reasoning engines.

At this point, in the long river of agent development history, several key technical puzzle pieces have all appeared: symbolicism provided the framework for logical reasoning, connectionism and reinforcement learning provided learning and decision-making capabilities, while large language models provided unprecedented world knowledge and general reasoning capabilities obtained through pre-training. In the next section, we will see how these technologies are integrated in the design of modern agents.

### 2.4.4 Agents Based on Large Language Models

With the rapid development of large language model technology, LLM-centric agents have become a new paradigm in the field of artificial intelligence. They can not only understand and generate human language but, more importantly, can autonomously perceive, plan, decide, and execute tasks through interaction with the environment.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-8.png" alt="Figure description" width="90%"/>
  <p>Figure 2.10 Core component architecture of LLM-driven agents</p>
</div>

As described in Chapter 1, the interaction between agents and the environment can be abstracted as a core loop. LLM-driven agents complete tasks through a continuously iterative closed-loop process where multiple modules work together. This process follows the architecture shown in Figure 2.10, with specific steps as follows:

1. **Perception**: The process begins with the **Perception Module**. It receives raw input from the **Environment** through sensors, forming **Observations**. This observation information (such as user instructions, data returned by APIs, or changes in environment state) is the starting point for agent decision-making and will be passed to the thinking stage after processing.
2. **Thought**: This is the cognitive core of the agent, corresponding to the collaborative work of the **Planning Module** and **Large Language Model (LLM)** in the diagram.
   - **Planning and Decomposition**: First, the planning module receives observation information and formulates high-level strategies. Through mechanisms such as **Reflection** and **Self-criticism**, it decomposes macro goals into more specific, executable steps.
   - **Reasoning and Decision-making**: Subsequently, the **LLM** as the hub receives instructions from the planning module and interacts with the **Memory** module to integrate historical information. The LLM performs deep reasoning and ultimately decides on the specific operation to execute next, typically manifested as a **Tool Call**.
3. **Action**: After decision-making is complete, the action stage begins, managed by the **Execution Module**. Tool call instructions generated by the LLM are sent to the execution module. This module parses instructions, selects and calls appropriate tools from the **Tool Use** toolbox (such as code executors, search engines, APIs, etc.) to interact with the environment or execute tasks. This actual interaction with the environment is the agent's **Action**.
4. **Observation** and Loop: Actions change the environment's state and produce results.
   - After tool execution, a **Tool Result** is returned to the LLM, constituting direct feedback on the action's effect. Simultaneously, the agent's action changes the environment, producing a completely new **environment state**.
   - This "tool result" and "new environment state" together constitute a new round of **Observation**. This new observation is captured again by the perception module, while the LLM **updates memory (Memory Update)** based on action results, thus initiating the next round of the "perceive-think-act" loop.

This modular collaborative mechanism and continuous iterative loop constitute the core workflow of LLM-driven agents solving complex problems.

### 2.4.5 Overview of Key Milestones in Agent Development

The development history of artificial intelligence agents is not a straight single-lane road but a process of interweaving, competition, and fusion of several core ideological schools over more than half a century. Understanding this process helps us gain insight into the profound origins of current agent architecture paradigm formation.

Among these, three major trends dominated research paradigms in different periods:

1. **Symbolism**: Represented by pioneers such as **Herbert A. Simon** and **Marvin Minsky**, believing that the core of intelligence lies in symbol manipulation and logical reasoning. This idea gave birth to SHRDLU, which could understand natural language instructions, knowledge-driven expert systems, and the "Deep Blue" computer that achieved great success in chess.
2. **Connectionism**: Its inspiration comes from simulating brain neural networks. Although early development was limited, under the promotion of researchers such as **Geoffrey Hinton**, the backpropagation algorithm laid the foundation for the revival of neural networks. Eventually, with the arrival of the deep learning era, this idea became mainstream through models such as convolutional neural networks and Transformers.
3. **Behaviorism**: Emphasizing that agents learn optimal strategies through interaction with the environment and trial and error, its modern incarnation is reinforcement learning. From early TD-Gammon to AlphaGo, which combined with deep learning and defeated top human players, this school endowed agents with the ability to learn complex decision-making behaviors from experience.

Entering the 2020s, these ideological schools have deeply integrated in unprecedented ways. Large language models represented by the GPT series are themselves products of connectionism but have become the core "brain" for executing symbolic reasoning, tool invocation, and planning decisions, forming a modern agent architecture combining neural and symbolic approaches. To systematically review this development context, Figure 2.11 below organizes key theories, projects, and events in the development history of artificial intelligence agents from the 1950s to the present, providing readers with a clear global overview as a consolidation of this chapter's knowledge.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-9.png" alt="Figure description" width="90%"/>
  <p>Figure 2.11 Timeline of agent development evolution (incomplete version)</p>
</div>

Thanks to breakthroughs in large language models, the agent technology stack presents unprecedented activity and diversity. Figure 2.12 shows a typical full view of the current AI Agent field technology stack, covering all aspects from underlying models to upper-layer applications.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-10.png" alt="Figure description" width="90%"/>
  <p>Figure 2.12 Overview of AI Agent technology stack</p>
</div>

This technology stack diagram was released by Letta in November 2024<sup>[10]</sup>. It layers and categorizes AI agent-related tools, platforms, and services, providing valuable reference for understanding current market landscape and technology selection.

## 2.5 Chapter Summary

This chapter reviewed the historical context of agent development, exploring the process from birth to evolution of its core ideas, covering several key paradigm revolutions in the field of artificial intelligence:

- **Exploration and Limitations of Symbolicism**: Starting from the classical era of artificial intelligence, this chapter explained how early agents represented by expert systems attempted to simulate intelligence through "knowledge + reasoning." By personally building a rule-based chatbot, we deeply experienced the capability boundaries of this paradigm and the fundamental challenges it faced.
- **Emergence of Distributed Intelligence Thinking**: Explored Marvin Minsky's "society of mind" theory. This revolutionary idea revealed that complex holistic intelligence can emerge from interactions of simple local units, providing important philosophical inspiration for subsequent multi-agent system research.
- **Evolution of Learning Paradigms**: Witnessed fundamental changes in how agents acquire capabilities. From connectionism endowing agents with the ability to perceive the world, to reinforcement learning enabling them to learn optimal decision-making in interactions with the environment, to large language models (LLMs) based on large-scale data pre-training providing them with unprecedented world knowledge and general reasoning capabilities.
- **Birth of Modern Agents**: Finally, we analyzed LLM-driven agents. Through analysis of their core components (models, memory, planning, tools, etc.) and working principles, we understood how various technical ideas in history achieved technological integration in modern Agent architecture.

Through this chapter's learning, we not only understand where the modern agents introduced in Chapter 1 came from but also established a macro cognitive framework about agent technology evolution. We can discover that agent development is not simple technical iteration but a thought revolution about how to define "intelligence," acquire "knowledge," and make "decisions."

Since the core of modern agents is large language models, deeply understanding their underlying principles is crucial. The next chapter will focus on large language models themselves, exploring their basic concepts, laying a solid foundation for subsequent advanced applications in multi-agent systems.

## Exercises

> **Note**: Some of the following exercises do not have standard answers, aiming to help learners establish systematic understanding of agent development history and cultivate "learning from history" technical insight.

1. The Physical Symbol System Hypothesis<sup>[1]</sup> is the theoretical cornerstone of the symbolicism era. Please analyze:

   - What do the "sufficiency assertion" and "necessity assertion" of this hypothesis mean?
   - Combined with this chapter's content, explain which problems encountered by symbolic agents in practice challenged the "sufficiency" of this hypothesis?
   - Do large language model-driven agents conform to the Physical Symbol System Hypothesis?

2. The expert system MYCIN<sup>[2]</sup> achieved significant success in the medical diagnosis field but was ultimately not widely applied in clinical practice. Please think:

   > **Hint**: Can analyze from multiple perspectives including technology, ethics, law, user acceptance, etc.

   - Besides the "knowledge acquisition bottleneck" and "brittleness" mentioned in this chapter, what other factors might have hindered the application of expert systems in high-risk fields like medicine?
   - If you were to design a medical diagnosis agent now, how would you design the system to overcome MYCIN's limitations?
   - In which vertical domains are rule-based expert systems still a better choice than deep learning today? Please give examples.

3. In Section 2.2, we implemented a simplified version of the ELIZA chatbot. Please expand on this basis:

   > **Hint**: This is a hands-on practice question; actual code writing is recommended

   - Add 3-5 new rules to ELIZA to enable it to handle more diverse conversation scenarios (such as discussing work, study, hobbies, etc.)
   - Implement a simple "contextual memory" function: allow ELIZA to remember key information mentioned by users in conversations (such as name, age, occupation) and reference it in subsequent conversations
   - Compare your expanded ELIZA with [ChatGPT](https://chatgpt.com/), listing at least 3 dimensions of essential differences
   - Why does the rule-based approach encounter "combinatorial explosion" problems and difficulty in scaling and maintenance when handling open-domain conversations? Can you explain using mathematical methods?

4. Marvin Minsky proposed a revolutionary viewpoint in the "society of mind" theory<sup>[7]</sup>: intelligence stems from collaboration of numerous simple agents, not a single perfect system.

   - In the Figure 2.6 "building a block tower" example, what would happen to the entire system if the `GRASP` agent suddenly failed? What are the advantages and disadvantages of this decentralized architecture?
   - Compare the "society of mind" theory with some current multi-agent systems (such as [CAMEL-Workforce](https://docs.camel-ai.org/key_modules/workforce), [MetaGPT](https://github.com/FoundationAgents/MetaGPT), [CrewAI](https://github.com/crewAIInc/crewAI)), what connections and differences exist between them?
   - Marvin Minsky believed agents could be "mindless" simple processes, yet current large language models and agents often possess powerful reasoning capabilities. Does this mean the "society of mind" theory is no longer applicable in the large language model era?

5. Reinforcement learning and supervised learning are two different learning paradigms. Please analyze:

   - Use AlphaGo's example to explain how reinforcement learning's "trial-and-error learning" mechanism works
   - Why is reinforcement learning particularly suitable for sequential decision problems? What is the essential difference in data requirements between it and supervised learning?
   - Now we need to train an agent to play Super Mario. If using supervised learning and reinforcement learning respectively, what data is needed for each? Which method is more suitable for this task?
   - In the training process of large language models, what key role does reinforcement learning play?

6. The pre-training-fine-tuning paradigm is an important breakthrough in the modern artificial intelligence field. Please think deeply:

   - Why does pre-training solve the "knowledge acquisition bottleneck" problem of the symbolicism era? What is the essential difference in knowledge representation methods?
   - Most knowledge of pre-trained models comes from internet data; what problems might this bring? How to mitigate these problems?
   - Do you think the "pre-training-fine-tuning" paradigm might be replaced by some new paradigm? Or will it exist long-term?

7. Suppose you want to design an "intelligent code review assistant" that can automatically review code submissions (Pull Requests), summarize code implementation logic, check code quality, discover potential bugs, and propose improvement suggestions.

   - If designing this system in the symbolicism era (1980s), how would you implement it? What difficulties would you encounter?
   - If in the deep learning era without large language models (around 2015), how would you implement it?
   - In the current era of large language models and agents, how would you design this agent's architecture? What modules should it include (refer to Figure 2.10)?
   - Comparing these three eras' solutions, explain how agent technology evolution made this task change from "almost impossible" to "feasible"

## References

[1] NEWELL A, SIMON H A. Computer science as empirical inquiry: symbols and search[J]. Communications of the ACM, 1976, 19(3): 113-126.

[2] BUCHANAN B G, SHORTLIFFE E H, ed. Rule-based expert systems: the MYCIN experiments of the Stanford Heuristic Programming Project[M]. Reading, Mass.: Addison-Wesley, 1984.

[3] WINOGRAD T. Understanding natural language[M]. New York: Academic Press, 1972.

[4] LENAT D B, GUHA R V. Cyc: a midterm report[J]. AI magazine, 1990, 11(3): 32.

[5] MCCARTHY J, HAYES P J. Some philosophical problems from the standpoint of artificial intelligence[C]//MELTZER B, MICHIE D, ed. Machine intelligence 4. Edinburgh: Edinburgh University Press, 1969: 463-502.

[6] WEIZENBAUM J. ELIZA: a computer program for the study of natural language communication between man and machine[J]. Communications of the ACM, 1966, 9(1): 36-45.

[7] MINSKY M. The society of mind[M]. New York: Simon & Schuster, 1986.

[8] RUMELHART D E, MCCLELLAND J L, PDP RESEARCH GROUP. Parallel distributed processing: explorations in the microstructure of cognition[M]. Cambridge, MA: MIT Press, 1986.

[9] SILVER D, HUANG A, MADDISON C J, ed. Mastering the game of Go with deep neural networks and tree search[J]. Nature, 2016, 529(7587): 484-489.

[10] LETTA. The AI agents stack[EB/OL]. (2024-11) [2025-09-07]. https://www.letta.com/blog/ai-agents-stack.

