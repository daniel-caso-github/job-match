from __future__ import annotations

from src.domain.entities.job import Job
from src.domain.ports.pitch_tailorer import PitchTailorer
from src.domain.ports.skill_gap_analyzer import SkillGapAnalyzer
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import ProfileForm, TechItem
from src.domain.value_objects.skill_gap_report import SkillGapReport
from src.infrastructure.orchestration.langgraph.postulation_graph import (
    build_postulation_graph,
)


class FakeSkillGapAnalyzer(SkillGapAnalyzer):
    def __init__(self, report: SkillGapReport):
        self.report = report
        self.calls: list[tuple[ProfileForm, Job]] = []

    def analyze(self, profile: ProfileForm, job: Job) -> SkillGapReport:
        self.calls.append((profile, job))
        return self.report


class FakePitchTailorer(PitchTailorer):
    def __init__(self, bullets: list[str], cover_letter: str):
        self.bullets = bullets
        self.cover_letter = cover_letter
        self.calls: list[tuple[ProfileForm, Job, SkillGapReport]] = []

    def tailor(
        self, profile: ProfileForm, job: Job, skill_gap: SkillGapReport
    ) -> tuple[list[str], str]:
        self.calls.append((profile, job, skill_gap))
        return self.bullets, self.cover_letter


def _profile() -> ProfileForm:
    return ProfileForm(
        username="d",
        stack=[TechItem(name="python", years=5)],
        seniority=Seniority.senior,
        english_level=EnglishLevel.b2,
        location="AR",
    )


def _job() -> Job:
    return Job.model_validate({
        "id": "abc",
        "source": "himalayas",
        "url": "https://x.com/j/1",
        "title": "Senior Backend Engineer",
        "raw_text": "We need Python experience.",
    })


def test_graph_runs_skill_gap_then_pitch_tailorer_in_order():
    report = SkillGapReport(met_requirements=["python"], gaps=["k8s"], confidence=0.9)
    analyzer = FakeSkillGapAnalyzer(report)
    tailorer = FakePitchTailorer(["bullet 1"], "cover letter")

    graph = build_postulation_graph(skill_gap_analyzer=analyzer, pitch_tailorer=tailorer)

    profile, job = _profile(), _job()
    state = {
        "profile": profile,
        "job": job,
        "skill_gap": None,
        "resume_bullets": [],
        "cover_letter": "",
    }
    result = graph.invoke(state)

    assert result["skill_gap"] == report
    assert result["resume_bullets"] == ["bullet 1"]
    assert result["cover_letter"] == "cover letter"

    # el tailorer recibió el skill_gap que produjo el analyst (dependencia secuencial)
    assert tailorer.calls[0][2] == report
    assert analyzer.calls == [(profile, job)]
