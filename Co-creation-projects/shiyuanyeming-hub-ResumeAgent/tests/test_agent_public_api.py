from resume_agent.domain.models import CareerFactBase, InterviewSession


class FakeSimpleAgent:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_hello_agents_runner_delegates_without_importing_framework():
    from resume_agent import HelloAgentsRunner

    agent = FakeSimpleAgent("answer")
    runner = HelloAgentsRunner(agent)

    assert runner.run("prompt") == "answer"
    assert agent.prompts == ["prompt"]


def test_public_builder_assembles_working_mentor_pair():
    from resume_agent import build_mentor_agents

    audit = FakeSimpleAgent(
        '{"dimension":"action","values":[{"text":"Built a dashboard"}]}'
    )
    question = FakeSimpleAgent('{"question":"你本人具体采取了什么行动？"}')
    pair = build_mentor_agents(audit, question)
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Analyst")
    session = InterviewSession(
        fact_base_id=base.id,
        active_experience_id=experience.id,
    )

    proposal = pair.fact_auditor.propose("I built a dashboard", session, base)

    assert proposal.experience_id == experience.id
    assert audit.prompts
    assert pair.question_writer is not None
