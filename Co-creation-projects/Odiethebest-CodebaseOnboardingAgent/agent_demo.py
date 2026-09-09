"""Optional HelloAgents adapter. Importing it does not create an API client."""
SYSTEM_PROMPT = '''You are a code onboarding assistant for the requests library.
Answer only from tool evidence. Every factual claim must include an observed
source ID in brackets, e.g. [auth.py#2]. Use search_code first, then read_symbol
or find_callers as needed. If evidence is insufficient, say so explicitly.
A citation ID confirms a location; it does not prove that a claim is true.'''

# hello-agents 0.2.7 builds ReAct messages from custom_prompt, not system_prompt.
REACT_PROMPT = SYSTEM_PROMPT + '''
Available tools:
{tools}
Question: {question}
History:
{history}
Respond with:
Thought: your next step
Action: tool_name[input]
The Action must occupy one line. To finish, use the action named Finish, with
its bracketed input containing your COMPLETE user-facing answer and source IDs.
Only the input of Finish is returned to the user; Thought is internal and is not
returned. Write the actual answer inside Finish, never a placeholder or label.
Keep the complete Finish action on a single line even for a detailed answer.
'''


def build_agent(llm, functions):
    from hello_agents import ReActAgent, ToolRegistry
    descriptions = {
        'search_code': 'Search code; returns evidence IDs and excerpts.',
        'file_outline': 'List symbols in a relative file path.',
        'read_symbol': 'Read source by evidence ID or unique symbol name.',
        'find_callers': 'Find possible callers by simple symbol name.',
    }
    registry = ToolRegistry()
    for name, description in descriptions.items():
        registry.register_function(name, description, functions[name])
    return ReActAgent(name='Codebase Onboarding Agent', llm=llm,
                      tool_registry=registry, custom_prompt=REACT_PROMPT, max_steps=14)


def completion_options(model):
    """Avoid legacy max_tokens/temperature for reasoning-model endpoints."""
    from openai import NOT_GIVEN
    if model.startswith(('gpt-5', 'o1', 'o3', 'o4')):
        return {'max_tokens': NOT_GIVEN, 'temperature': NOT_GIVEN,
                'max_completion_tokens': 4096}
    return {'max_tokens': 4096}


def configured_llm():
    from hello_agents import HelloAgentsLLM

    class CompatibleLLM(HelloAgentsLLM):
        def invoke(self, messages, **kwargs):
            options = completion_options(self.model)
            options.update(kwargs)
            return super().invoke(messages, **options)

    return CompatibleLLM()
