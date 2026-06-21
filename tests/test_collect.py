"""Tests for diversity-aware candidate selection (per-company / per-provider caps)."""

from job_hunter.models import Job
from job_hunter.phases.collect import _select_diverse


def _job(company, source="ats", i=0) -> Job:
    return Job(source=source, title=f"Engineer {i}", company=company, url=f"http://x/{company}/{i}")


def test_per_company_cap_limits_one_employer():
    jobs = [_job("Databricks", i=i) for i in range(10)] + [_job("Stripe", i=i) for i in range(3)]
    out = _select_diverse(jobs, keep=100, per_company=2, per_provider=0)
    companies = [j.company for j in out]
    assert companies.count("Databricks") == 2
    assert companies.count("Stripe") == 2  # only 3 existed but cap is 2


def test_keep_limit_respected():
    jobs = [_job(f"Co{i}", i=i) for i in range(50)]
    out = _select_diverse(jobs, keep=10, per_company=0, per_provider=0)
    assert len(out) == 10


def test_per_provider_cap():
    jobs = [_job("A", source="ats", i=i) for i in range(5)] + [_job("B", source="adzuna")]
    out = _select_diverse(jobs, keep=100, per_company=0, per_provider=3)
    assert sum(1 for j in out if j.source.startswith("ats")) == 3
    assert sum(1 for j in out if j.source == "adzuna") == 1


def test_caps_off_keeps_everything():
    jobs = [_job("A", i=i) for i in range(5)]
    out = _select_diverse(jobs, keep=100, per_company=0, per_provider=0)
    assert len(out) == 5
