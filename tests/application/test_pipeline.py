from __future__ import annotations

from unittest.mock import MagicMock, patch

MODULE = "src.interfaces.pipeline"


def _mock_cm(session: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    return cm


def test_run_collect_returns_use_case_result():
    session = MagicMock()
    with (
        patch(f"{MODULE}.session_scope", return_value=_mock_cm(session)),
        patch(f"{MODULE}.CollectJobsUseCase") as MockUC,
        patch(f"{MODULE}.HimalayasSource"),
        patch(f"{MODULE}.RemotiveSource"),
        patch(f"{MODULE}.SqlAlchemyJobRepository"),
    ):
        MockUC.return_value.execute.return_value = 7
        from src.interfaces.pipeline import run_collect

        assert run_collect() == 7
        MockUC.return_value.execute.assert_called_once()


def test_run_extract_forwards_limit():
    session = MagicMock()
    with (
        patch(f"{MODULE}.session_scope", return_value=_mock_cm(session)),
        patch(f"{MODULE}.ExtractJobRequirementsUseCase") as MockUC,
        patch(f"{MODULE}.GeminiExtractor"),
        patch(f"{MODULE}.SqlAlchemyJobRepository"),
    ):
        MockUC.return_value.execute.return_value = 3
        from src.interfaces.pipeline import run_extract

        assert run_extract(limit=50) == 3
        MockUC.return_value.execute.assert_called_once_with(limit=50)


def test_run_embed_forwards_limit():
    session = MagicMock()
    with (
        patch(f"{MODULE}.session_scope", return_value=_mock_cm(session)),
        patch(f"{MODULE}.EmbedJobsUseCase") as MockUC,
        patch(f"{MODULE}._embedder_singleton"),
        patch(f"{MODULE}.SqlAlchemyJobRepository"),
    ):
        MockUC.return_value.execute.return_value = 10
        from src.interfaces.pipeline import run_embed

        assert run_embed(limit=100) == 10
        MockUC.return_value.execute.assert_called_once_with(limit=100)


def test_run_score_all_profiles_returns_counts_per_profile():
    session = MagicMock()
    profile = MagicMock()
    profile.form.username = "profile-1"

    with (
        patch(f"{MODULE}.session_scope", return_value=_mock_cm(session)),
        patch(f"{MODULE}.SqlAlchemyProfileRepository") as MockProfRepo,
        patch(f"{MODULE}.SqlAlchemyJobRepository"),
        patch(f"{MODULE}.SqlAlchemyMatchRepository"),
        patch(f"{MODULE}.ScoreProfileUseCase") as MockUC,
        patch(f"{MODULE}._embedder_singleton"),
        patch(f"{MODULE}.GeminiScorer"),
    ):
        MockProfRepo.return_value.list_all.return_value = [profile]
        MockUC.return_value.execute.return_value = 5
        from src.interfaces.pipeline import run_score_all_profiles

        assert run_score_all_profiles() == {"profile-1": 5}
