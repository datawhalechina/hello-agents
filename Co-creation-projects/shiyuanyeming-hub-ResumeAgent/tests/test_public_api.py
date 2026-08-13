def test_public_api_imports():
    from resume_agent import (
        CareerFactBase,
        InterviewService,
        QuestionPlanner,
        SQLiteFactBaseRepository,
        VersionService,
    )

    assert CareerFactBase is not None
    assert InterviewService is not None
    assert QuestionPlanner is not None
    assert SQLiteFactBaseRepository is not None
    assert VersionService is not None
