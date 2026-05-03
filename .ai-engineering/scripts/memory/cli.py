"""spec-118 T-2.3 -- Typer CLI surface for the memory layer.

Exposes `ai-eng memory ...` subcommands. Hooks shell to this CLI through
subprocess so heavy imports (fastembed, hdbscan) stay off the hook critical
path. The CLI itself remains lazy where possible: `remember` and `dream`
import semantic/dreaming modules only when invoked.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import typer

# Allow standalone execution as `python3 -m memory.cli`. The package lives at
# `.ai-engineering/scripts/memory/`; resolve that path before importing siblings.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent))

from memory import audit, episodic, knowledge, repair, store  # noqa: E402

app = typer.Typer(
    name="memory",
    help="spec-118 Memory Layer: episodic + knowledge object + semantic retrieval.",
    no_args_is_help=True,
)


def _project_root(path: Path | None = None) -> Path:
    return path or Path.cwd()


def _ms_since(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Show counts, schema version, last dream-run."""
    root = _project_root()
    store.bootstrap(root)
    with store.connect(root) as conn:
        version = store.schema_version(conn)
        episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        kos_total = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
        kos_active = conn.execute(
            "SELECT COUNT(*) FROM knowledge_objects WHERE archived = 0"
        ).fetchone()[0]
        retrievals = conn.execute("SELECT COUNT(*) FROM retrieval_log").fetchone()[0]
        pending_embed = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding_status = 'pending'"
        ).fetchone()[0]

    payload = {
        "schema_version": version,
        "db_path": str(store.db_path(root)),
        "episodes": episodes,
        "knowledge_objects_total": kos_total,
        "knowledge_objects_active": kos_active,
        "retrievals_logged": retrievals,
        "episodes_pending_embedding": pending_embed,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo("memory layer status:")
        for k, v in payload.items():
            typer.echo(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    source: str = typer.Option(
        "all",
        "--source",
        help="lessons | decisions | instincts | all",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Hash and upsert knowledge objects from canonical sources."""
    root = _project_root()
    store.bootstrap(root)
    counts: dict[str, int] = {}
    with store.connect(root) as conn:
        if source in ("lessons", "all"):
            counts["lesson"] = knowledge.ingest_lessons(conn, root)
        if source in ("decisions", "all"):
            counts["decision"] = knowledge.ingest_decisions(conn, root)
        if source in ("instincts", "all"):
            counts["instinct"] = knowledge.ingest_instincts(conn, root)
        conn.commit()

    # Emit one memory_event per source family so the audit chain reflects the
    # ingest. Per WARN-6 source = "cli".
    for ko_kind, n in counts.items():
        if n > 0:
            audit.emit(
                root,
                operation=audit.Operation.KNOWLEDGE_OBJECT_ADDED,
                source="cli",
                detail={"ko_kind": ko_kind, "result_count": n},
            )

    if json_out:
        typer.echo(json.dumps(counts, indent=2))
    else:
        for k, v in counts.items():
            typer.echo(f"  {k}: +{v}")


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------


@app.command()
def repair_cmd(
    backfill_timestamps: bool = typer.Option(
        False,
        "--backfill-timestamps",
        help="Fill empty `timestamp` fields in instinct-observations.ndjson.",
    ),
    rebuild_vectors: bool = typer.Option(
        False,
        "--rebuild-vectors",
        help="Re-embed every knowledge object and episode (Phase 3+).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Data-hygiene utilities. Idempotent."""
    root = _project_root()
    if not (backfill_timestamps or rebuild_vectors):
        raise typer.BadParameter("specify at least one repair flag")

    payload: dict = {}
    if backfill_timestamps:
        report = repair.backfill_timestamps(root)
        payload["backfill_timestamps"] = report.__dict__

    if rebuild_vectors:
        # Phase 3 placeholder; semantic.py adds the body.
        payload["rebuild_vectors"] = {
            "status": "not_implemented",
            "message": "Available after Phase 3 semantic tier ships.",
        }

    if json_out:
        typer.echo(json.dumps(payload, indent=2, default=str))
    else:
        typer.echo(json.dumps(payload, indent=2, default=str))


# Typer collides with the `repair` module name; expose the command as `repair`.
app.command(name="repair")(repair_cmd)


# ---------------------------------------------------------------------------
# stop (called by memory-stop.py hook)
# ---------------------------------------------------------------------------


@app.command()
def stop(
    session_id: str = typer.Option(..., "--session-id"),
    plane: str | None = typer.Option(None, "--plane"),
    skip_embed: bool = typer.Option(False, "--skip-embed", help="Skip fire-and-forget embed."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Persist the current session as an episode and emit `episode_stored`.

    The synchronous SQLite write completes inside the Stop hook budget; a
    detached child subprocess (`embed-episode`) handles fastembed asynchronously
    and emits a second `episode_stored` event with `embedding_status=complete`
    once the vector is upserted (per WARN-4 from T-1.8 governance).
    """
    root = _project_root()
    t0 = time.monotonic()
    row = episodic.write_episode(root, session_id=session_id, plane=plane)
    if row is None:
        if json_out:
            typer.echo(json.dumps({"status": "no_events"}))
        else:
            typer.echo("no session events; nothing to write")
        return

    duration_ms = _ms_since(t0)
    audit.emit_episode_stored(
        root,
        episode_id=row.episode_id,
        embedding_status=row.embedding_status,
        duration_ms=duration_ms,
        source="hook",
        session_id=session_id,
    )

    if not skip_embed:
        # Fire-and-forget child: detach via subprocess.Popen with no wait().
        import os
        import subprocess

        scripts_dir = Path(__file__).resolve().parent.parent
        child_env = {
            **os.environ,
            "PYTHONPATH": str(scripts_dir) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "memory.cli",
                    "embed-episode",
                    "--episode-id",
                    row.episode_id,
                ],
                cwd=str(root),
                env=child_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            pass

    payload = {
        "episode_id": row.episode_id,
        "session_id": row.session_id,
        "duration_ms": duration_ms,
        "embedding_status": row.embedding_status,
        "embed_dispatched": not skip_embed,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"episode_stored {row.episode_id} ({duration_ms}ms)")


@app.command(name="embed-all")
def embed_all_cmd(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Embed every active KO and pending episode that lacks a vector."""
    from memory import semantic, store

    root = _project_root()
    store.bootstrap(root)
    embedded_kos = 0
    embedded_episodes = 0

    with store.connect(root) as conn:
        kos = conn.execute(
            """
            SELECT ko.ko_hash, ko.canonical_text
            FROM knowledge_objects ko
            LEFT JOIN vector_map vm
              ON vm.target_kind = 'knowledge_object' AND vm.target_id = ko.ko_hash
            WHERE ko.archived = 0 AND vm.rowid IS NULL
            """
        ).fetchall()
        episodes = conn.execute(
            """
            SELECT episode_id, summary FROM episodes
            WHERE embedding_status != 'complete'
            """
        ).fetchall()

    for row in kos:
        try:
            semantic.embed_and_upsert_ko(root, ko_hash=row["ko_hash"], text=row["canonical_text"])
            embedded_kos += 1
        except Exception:
            continue

    for row in episodes:
        try:
            semantic.embed_and_upsert_episode(
                root, episode_id=row["episode_id"], text=row["summary"]
            )
            embedded_episodes += 1
        except Exception:
            continue

    payload = {
        "embedded_knowledge_objects": embedded_kos,
        "embedded_episodes": embedded_episodes,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"embedded {embedded_kos} KOs + {embedded_episodes} episodes")


@app.command(name="embed-episode")
def embed_episode_cmd(
    episode_id: str = typer.Option(..., "--episode-id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Embed one episode summary asynchronously (called by `stop`)."""
    from memory import semantic, store

    root = _project_root()
    with store.connect(root) as conn:
        row = conn.execute(
            "SELECT summary FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
    if row is None:
        if json_out:
            typer.echo(json.dumps({"status": "no_episode"}))
        return

    t0 = time.monotonic()
    try:
        rowid = semantic.embed_and_upsert_episode(root, episode_id=episode_id, text=row["summary"])
        status = "complete" if rowid is not None else "failed"
        failure_reason = None if rowid is not None else "vec0 unavailable"
    except Exception as exc:
        status = "failed"
        failure_reason = str(exc)[:200]

    duration_ms = _ms_since(t0)
    detail = {
        "episode_id": episode_id,
        "embedding_status": status,
        "duration_ms": duration_ms,
    }
    if failure_reason:
        detail["failure_reason"] = failure_reason
    audit.emit(
        root,
        operation=audit.Operation.EPISODE_STORED,
        source="cli",
        detail=detail,
    )

    if json_out:
        typer.echo(json.dumps(detail, indent=2))


# ---------------------------------------------------------------------------
# warmup, remember, dream -- Phase 3+ stubs
# ---------------------------------------------------------------------------


@app.command()
def warmup(json_out: bool = typer.Option(False, "--json")) -> None:
    """Pre-download fastembed ONNX weights. First call may take 30+ seconds."""
    from memory import semantic

    info = semantic.warmup()
    if json_out:
        typer.echo(json.dumps(info, indent=2))
    else:
        typer.echo(f"warmed model={info['model_name']} dim={info['dim']}")


@app.command()
def remember(
    query: str = typer.Argument(..., help="Free-text query."),
    kind: str | None = typer.Option(None, "--kind", help="episode | knowledge"),
    since: str | None = typer.Option(None, "--since", help="e.g. 7d"),
    top_k: int = typer.Option(10, "--top-k"),
    debug: bool = typer.Option(False, "--debug"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Top-K cross-session retrieval (decayed_importance * cosine)."""
    from memory import retrieval

    out = retrieval.search(
        _project_root(),
        query=query,
        top_k=top_k,
        kind_filter=kind,
        since=since,
    )
    if json_out:
        typer.echo(json.dumps(out, indent=2))
        return
    if out.get("status") != "ok":
        typer.echo(f"status: {out.get('status')} -- {out.get('message', '')}")
        return
    typer.echo(f"results ({out['result_count']}, {out['duration_ms']}ms):")
    for r in out["results"]:
        score_line = f"  {r['target_kind']:18s} {r['target_id'][:12]} score={r['score']:.4f}"
        if debug:
            score_line += f" cos={r['cosine']:.4f} decay={r['decayed_importance']:.4f} age={r['days_old']:.1f}d"
        typer.echo(score_line)
        if r["summary"]:
            typer.echo(f"      {r['summary'][:160]}")


@app.command()
def dream(
    dry_run: bool = typer.Option(False, "--dry-run"),
    decay_only: bool = typer.Option(False, "--decay-only"),
    min_cluster_size: int = typer.Option(3, "--min-cluster-size"),
    decay_base: float = typer.Option(0.97, "--decay-base"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Consolidation: decay + HDBSCAN cluster + supersedence + proposals.

    Per D-118-04 NEVER mutates LESSONS.md. Promotion candidates land in
    `.ai-engineering/instincts/memory-proposals.md` for human review.
    """
    from memory import dreaming

    report = dreaming.run_dream(
        _project_root(),
        dry_run=dry_run,
        decay_only=decay_only,
        min_cluster_size=min_cluster_size,
        decay_base=decay_base,
    )
    payload = {
        "outcome": report.outcome,
        "dry_run": report.dry_run,
        "decay_factor": report.decay_factor,
        "decayed_count": report.decayed_count,
        "clusters_found": report.clusters_found,
        "promoted_count": report.promoted_count,
        "retired_count": report.retired_count,
        "proposals_path": report.proposals_path,
        "duration_ms": report.duration_ms,
    }
    if json_out:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"dream {report.outcome} ({report.duration_ms}ms)")
    typer.echo(f"  decayed={report.decayed_count}")
    typer.echo(f"  clusters={report.clusters_found}")
    typer.echo(f"  promoted={report.promoted_count}")
    typer.echo(f"  retired={report.retired_count}")
    typer.echo(f"  proposals: {report.proposals_path}")


def main() -> None:
    """Entry point for `python3 -m memory.cli`."""
    app()


if __name__ == "__main__":
    main()
