def test_public_api_imports():
    from resume_agent import (
        CareerFactBase,
        CandidateProfile,
        InterviewService,
        QuestionPlanner,
        RenderFormat,
        ResumeRenderer,
        ResumeRenderService,
        SQLiteFactBaseRepository,
        VersionService,
    )

    assert CareerFactBase is not None
    assert CandidateProfile is not None
    assert InterviewService is not None
    assert QuestionPlanner is not None
    assert SQLiteFactBaseRepository is not None
    assert RenderFormat is not None
    assert ResumeRenderer is not None
    assert ResumeRenderService is not None
    assert VersionService is not None
