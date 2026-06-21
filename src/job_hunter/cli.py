"""Command-line entrypoint with phased subcommands.

    job-hunter run       # phase 1 + 2 + 3 (default)
    job-hunter collect   # phase 1 only  -> phase1_candidates.json
    job-hunter enrich    # phase 2 only  -> phase2_enriched.json
    job-hunter rank      # phase 3 only  -> role files

The phases flow one into the other through JSON artifacts in the work dir, so you can
re-run any phase without redoing the others (e.g. tweak scoring and just `rank`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from job_hunter.phases.collect import CollectConfig, collect
from job_hunter.phases.enrich import EnrichConfig, enrich
from job_hunter.phases.rank import RankConfig, rank
from job_hunter.pipeline import RunConfig, run
from job_hunter.providers import ALL_PROVIDERS

console = Console()
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
PERSONAS_DIR = DATA / "personas"
DEFAULT_PERSONA = "example"


def build_parser() -> argparse.ArgumentParser:
    # Shared persona/path options — usable both before and after the subcommand,
    # e.g. `job-hunter --persona alex run` or `job-hunter run --persona alex`.
    # SUPPRESS so a value given before the subcommand isn't clobbered by the
    # subparser's default; real defaults are applied in _resolve().
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--persona", default=argparse.SUPPRESS,
                        help=f"persona id -> data/personas/<id>.yaml (default: {DEFAULT_PERSONA})")
    common.add_argument("--profile", default=argparse.SUPPRESS,
                        help="explicit persona YAML path (overrides --persona)")
    common.add_argument("--work", default=argparse.SUPPRESS,
                        help="phase-artifact dir (default: data/work/<persona>)")
    common.add_argument("--out", default=argparse.SUPPRESS,
                        help="final role-file dir (default: data/roles/<persona>)")

    p = argparse.ArgumentParser(prog="job-hunter", description=__doc__.splitlines()[0],
                                parents=[common])
    sub = p.add_subparsers(dest="cmd")

    def add_collect_args(sp):
        sp.add_argument("--providers", nargs="+", default=list(ALL_PROVIDERS), choices=list(ALL_PROVIDERS))
        sp.add_argument("--include-unknown", action="store_true", help="keep non-reputable employers")
        sp.add_argument("--anywhere", action="store_true", help="don't restrict to CH/IE/NL/UK/remote")
        sp.add_argument("--no-role-gate", action="store_true", help="don't require dev/quant/DS titles")
        sp.add_argument("--prescreen-min", type=int, default=45)

    def add_enrich_args(sp):
        sp.add_argument("--enrich-top", type=int, default=25, help="how many candidates phase 2 evaluates")
        sp.add_argument("--no-refetch", action="store_true", help="skip re-fetching live pages")
        sp.add_argument("--llm", action="store_true", help="use Claude Haiku (needs ANTHROPIC_API_KEY)")

    def add_rank_args(sp):
        sp.add_argument("--final-min", type=int, default=0)
        sp.add_argument("--top", type=int, default=60)

    sp_run = sub.add_parser("run", parents=[common], help="all three phases (default)")
    add_collect_args(sp_run)
    add_enrich_args(sp_run)
    add_rank_args(sp_run)

    add_collect_args(sub.add_parser("collect", parents=[common], help="phase 1 only"))
    add_enrich_args(sub.add_parser("enrich", parents=[common], help="phase 2 only"))
    add_rank_args(sub.add_parser("rank", parents=[common], help="phase 3 only"))
    return p


def _show(jobs):
    if not jobs:
        console.print("[yellow]No roles. Try --include-unknown, --anywhere, or lower --prescreen-min.[/]")
        return
    table = Table(title="Top roles by fit")
    for col in ("Tier", "Fit", "AI", "Company", "Role", "Country", "Salary"):
        table.add_column(col, justify="right" if col in ("Tier", "Fit", "AI") else "left")
    for j in jobs[:25]:
        ai = f"{j.ai_score}%" if j.ai_score is not None else "—"
        table.add_row(str(j.tier), f"{j.final_score or j.fit_score}%", ai, j.company,
                      j.title[:42], j.country or "—", j.salary_text)
    console.print(table)


def _resolve(args) -> tuple[str, str, str, str]:
    """Turn --persona / --profile into (profile_path, work_dir, out_dir, tiers_path).

    Each persona gets its own work + output dirs (and manual-tier sidecar) so results
    and curation are stored per persona.
    """
    profile = getattr(args, "profile", None)
    if profile:
        profile_path = Path(profile)
        persona_id = profile_path.stem
    else:
        persona_id = getattr(args, "persona", DEFAULT_PERSONA)
        profile_path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not profile_path.exists():
        available = sorted(p.stem for p in PERSONAS_DIR.glob("*.yaml") if p.stem != "_template")
        console.print(f"[red]Persona not found:[/] {profile_path}")
        console.print(f"Available: [cyan]{', '.join(available) or '(none)'}[/]")
        console.print("Create one with: [dim]cp data/personas/_template.yaml data/personas/<id>.yaml[/]")
        raise SystemExit(2)
    work = Path(getattr(args, "work", None) or DATA / "work" / persona_id)
    out = Path(getattr(args, "out", None) or DATA / "roles" / persona_id)
    tiers_path = DATA / "tiers" / f"{persona_id}.json"
    return str(profile_path), str(work), str(out), str(tiers_path)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:  # bare `job-hunter` -> full run with defaults
        args = parser.parse_args(list(argv or []) + ["run"])
    cmd = args.cmd
    profile_path, work, out, tiers_path = _resolve(args)

    try:
        return _dispatch(cmd, args, profile_path, work, out, tiers_path)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Can't run:[/] {exc}")
        return 2


def _dispatch(cmd, args, profile_path, work, out, tiers_path) -> int:
    if cmd == "collect":
        collect(CollectConfig(
            profile_path=profile_path, work_dir=work, providers=args.providers,
            reputable_only=not args.include_unknown, countries_only=not args.anywhere,
            role_gate=not args.no_role_gate, prescreen_min=args.prescreen_min,
        ))
    elif cmd == "enrich":
        enrich(EnrichConfig(
            profile_path=profile_path, work_dir=work, top_n=args.enrich_top,
            refetch_pages=not args.no_refetch, use_llm=args.llm,
        ))
    elif cmd == "rank":
        jobs = rank(RankConfig(
            work_dir=work, out_dir=out, final_min=args.final_min, top_n=args.top,
            tiers_path=tiers_path,
        ))
        _show(jobs)
    else:  # run
        jobs = run(RunConfig(
            profile_path=profile_path, work_dir=work, out_dir=out, providers=args.providers,
            reputable_only=not args.include_unknown, countries_only=not args.anywhere,
            role_gate=not args.no_role_gate, prescreen_min=args.prescreen_min,
            enrich_top=args.enrich_top, refetch_pages=not args.no_refetch, use_llm=args.llm,
            final_min=args.final_min, top_n=args.top, tiers_path=tiers_path,
        ))
        _show(jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
