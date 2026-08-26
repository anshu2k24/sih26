"""
ertmac.audit.report_writer
===========================
Write Checkpoint-1 findings to:
  - reports/audit_schema.md
  - reports/audit_data_quality.md
  - reports/audit_well_coverage.md
  - reports/audit_report.html  (full visual report)
  - reports/tables/*.csv       (raw tables for reuse)
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, BaseLoader

from ertmac.utils.logging_setup import get_logger
from ertmac.utils.paths import REPORTS_DIR, TABLES_DIR, FIGURES_DIR

log = get_logger(__name__)

_NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _df_to_md(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a GitHub-flavoured Markdown table."""
    return df.to_markdown(index=False)


def _save_csv(df: pd.DataFrame, name: str) -> Path:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    log.info("Saved table: %s", path.name)
    return path


# ── Markdown reports ──────────────────────────────────────────────────────────

def write_schema_report(schema_result: dict[str, Any]) -> Path:
    """Write reports/audit_schema.md."""
    arrow = schema_result["arrow_schema"]
    duckdb_schema = schema_result["duckdb_schema"]
    nested = schema_result["nested_columns"]

    lines: list[str] = [
        "# Checkpoint 1 — Schema Report",
        f"\n_Generated: {_NOW}_\n",
        "## File Summary\n",
        f"| Property | Value |",
        f"|---|---|",
        f"| Rows | {arrow['num_rows']:,} |",
        f"| Top-level Columns | {arrow['num_columns']} |",
        f"| Row Groups | {arrow['num_row_groups']} |",
        f"| Serialized Size | {arrow['serialized_size_bytes']:,} bytes |",
        "",
        "## Top-Level Column Schema (PyArrow)\n",
        "| # | Column | PyArrow Type | Nullable |",
        "|---|---|---|---|",
    ]
    for c in arrow["columns"]:
        lines.append(f"| {c['index']} | `{c['name']}` | `{c['pa_type']}` | {c['nullable']} |")

    lines += [
        "",
        "## DuckDB Column Types\n",
        "| Column | DuckDB Type | Nullable |",
        "|---|---|---|",
    ]
    for r in duckdb_schema:
        lines.append(f"| `{r['column_name']}` | `{r['column_type']}` | {r['null']} |")

    lines += ["", "## Nested Array Columns — Sub-field Inventory\n"]
    for col, info in nested.items():
        lines += [
            f"### `{col}`\n",
            f"- **Total parent rows**: {info['total_parent_rows']:,}",
            f"- **Rows with ≥1 record**: {info['rows_with_nonempty_array']:,} "
            f"({info['rows_with_nonempty_array']/info['total_parent_rows']*100:.1f}%)",
            f"- **Total nested records**: {info['total_nested_records']:,}",
            f"- **Discovered sub-fields**: {', '.join(f'`{f}`' for f in info['sub_fields']) or '_none discovered_'}",
            "",
        ]

    text = "\n".join(lines)
    path = REPORTS_DIR / "audit_schema.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    log.info("Wrote: %s", path.name)
    return path


def write_data_quality_report(dq: dict[str, pd.DataFrame]) -> Path:
    """Write reports/audit_data_quality.md and save CSVs."""
    _save_csv(dq["top_level"], "dq_top_level")
    _save_csv(dq["nested_coverage"], "dq_nested_coverage")
    _save_csv(dq["statusinfo_sentinels"], "dq_statusinfo_sentinels")
    _save_csv(dq["date_parseability"], "dq_date_parseability")

    lines = [
        "# Checkpoint 1 — Data Quality Report",
        f"\n_Generated: {_NOW}_\n",
        "> **SENTINEL RULE**: The value `-999.99` is NOT a real measurement.",
        "> It must be converted to `NaN` before any computation or ML training.\n",
        "## Top-Level Column Quality\n",
        _df_to_md(dq["top_level"]),
        "",
        "## Nested Array Coverage (Parent Row Level)\n",
        _df_to_md(dq["nested_coverage"]),
        "",
        "## `statusInfo` Numeric Fields — Sentinel & NULL Rates\n",
        "> Fields stored as VARCHAR in WITSML; require type casting after sentinel removal.\n",
        _df_to_md(dq["statusinfo_sentinels"]),
        "",
        "## Timestamp Parseability\n",
        _df_to_md(dq["date_parseability"]),
    ]

    text = "\n".join(lines)
    path = REPORTS_DIR / "audit_data_quality.md"
    path.write_text(text, encoding="utf-8")
    log.info("Wrote: %s", path.name)
    return path


def write_well_coverage_report(wc: dict[str, pd.DataFrame]) -> Path:
    """Write reports/audit_well_coverage.md and save CSVs."""
    _save_csv(wc["report_counts"], "wc_report_counts")
    _save_csv(wc["operator_rig"], "wc_operator_rig")
    _save_csv(wc["depth_coverage"], "wc_depth_coverage")
    _save_csv(wc["spud_completion"], "wc_spud_completion")

    rc = wc["report_counts"]
    total_reports = rc["report_count"].sum()
    date_min = rc["earliest_report"].min()
    date_max = rc["latest_report"].max()

    lines = [
        "# Checkpoint 1 — Well & Wellbore Coverage Report",
        f"\n_Generated: {_NOW}_\n",
        "## Summary\n",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total DDR reports | {total_reports:,} |",
        f"| Distinct wells | {rc['nameWell'].nunique()} |",
        f"| Distinct wellbores | {len(rc)} |",
        f"| Earliest report date | {date_min} |",
        f"| Latest report date | {date_max} |",
        "",
        "## Report Counts per Wellbore\n",
        _df_to_md(rc),
        "",
        "## Operators & Drilling Rigs\n",
        _df_to_md(wc["operator_rig"]),
        "",
        "## Depth Coverage per Wellbore (MD / TVD)\n",
        "> MD and TVD are sourced from `statusInfo`. Sentinel `-999.99` excluded.\n",
        _df_to_md(wc["depth_coverage"]),
        "",
        "## Spud & Completion Dates\n",
        _df_to_md(wc["spud_completion"]),
    ]

    text = "\n".join(lines)
    path = REPORTS_DIR / "audit_well_coverage.md"
    path.write_text(text, encoding="utf-8")
    log.info("Wrote: %s", path.name)
    return path


# ── HTML report ───────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>eRTMAC-NWIS — Checkpoint 1 Audit Report</title>
  <style>
    :root {
      --bg: #1e1e2e; --surface: #2a2a3e; --border: #44475a;
      --text: #cdd6f4; --accent: #89b4fa; --warn: #f38ba8;
      --ok: #a6e3a1; --muted: #6c7086;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; padding: 2rem; }
    h1 { color: var(--accent); font-size: 2rem; margin-bottom: 0.3rem; }
    h2 { color: var(--accent); font-size: 1.4rem; margin: 2rem 0 0.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
    h3 { color: var(--ok); font-size: 1.1rem; margin: 1.2rem 0 0.5rem; }
    .subtitle { color: var(--muted); margin-bottom: 2rem; font-size: 0.95rem; }
    .badge { display: inline-block; background: var(--surface); border: 1px solid var(--border);
             padding: 0.2rem 0.7rem; border-radius: 12px; font-size: 0.85rem; margin: 0.2rem; }
    .warn { color: var(--warn); }
    .ok { color: var(--ok); }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.88rem; }
    th { background: var(--surface); color: var(--accent); padding: 0.5rem 0.8rem; text-align: left; border: 1px solid var(--border); }
    td { padding: 0.4rem 0.8rem; border: 1px solid var(--border); }
    tr:nth-child(even) td { background: rgba(255,255,255,0.03); }
    .figures { display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 1.5rem; margin: 1.5rem 0; }
    .fig-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    .fig-card img { width: 100%; display: block; }
    .fig-caption { padding: 0.5rem 0.8rem; font-size: 0.85rem; color: var(--muted); }
    .callout { background: var(--surface); border-left: 4px solid var(--warn); padding: 0.8rem 1rem; margin: 1rem 0; border-radius: 4px; }
    .callout.ok { border-left-color: var(--ok); }
    pre { background: var(--surface); padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }
    .stat-card .value { font-size: 2rem; font-weight: bold; color: var(--accent); }
    .stat-card .label { font-size: 0.82rem; color: var(--muted); margin-top: 0.3rem; }
  </style>
</head>
<body>
  <h1>🛢️ eRTMAC-NWIS — Checkpoint 1: Raw Data Audit</h1>
  <p class="subtitle">
    SIH 2026 PS26121 &nbsp;|&nbsp; Equinor Volve Open Dataset (Validation)
    &nbsp;|&nbsp; Generated: {{ generated_at }}
  </p>

  <div class="callout">
    <strong>⚠️ SENTINEL RULE:</strong> The value <code>-999.99</code> is <strong>NOT</strong> a real measurement.
    It must be converted to <code>NaN</code> before any computation or ML training. This is flagged throughout this report.
  </div>

  <h2>Dataset Summary</h2>
  <div class="summary-grid">
    <div class="stat-card"><div class="value">{{ num_rows }}</div><div class="label">DDR Reports</div></div>
    <div class="stat-card"><div class="value">{{ num_cols }}</div><div class="label">Top-level Columns</div></div>
    <div class="stat-card"><div class="value">{{ num_wellbores }}</div><div class="label">Distinct Wellbores</div></div>
    <div class="stat-card"><div class="value">{{ num_wells }}</div><div class="label">Distinct Wells</div></div>
    <div class="stat-card"><div class="value">{{ date_min }}</div><div class="label">Earliest Report</div></div>
    <div class="stat-card"><div class="value">{{ date_max }}</div><div class="label">Latest Report</div></div>
    <div class="stat-card"><div class="value">{{ total_activity }}</div><div class="label">Activity Records</div></div>
    <div class="stat-card"><div class="value">{{ total_fluid }}</div><div class="label">Fluid Records</div></div>
  </div>

  <h2>Schema</h2>
  <h3>Top-Level Columns</h3>
  {{ schema_table | safe }}

  <h3>Nested Array Columns</h3>
  {{ nested_table | safe }}

  <h2>Data Quality</h2>
  <h3>Top-Level Column Null & Sentinel Rates</h3>
  {{ dq_top_level_table | safe }}

  <h3>statusInfo Numeric Fields — Sentinel & NULL Rates</h3>
  <div class="callout">
    Numeric measurements in <code>statusInfo</code> are stored as <code>VARCHAR</code> strings in WITSML.
    All fields require sentinel removal and type casting before use.
  </div>
  {{ dq_statusinfo_table | safe }}

  <h3>Nested Array Coverage</h3>
  {{ nested_coverage_table | safe }}

  <h2>Well & Wellbore Coverage</h2>
  {{ well_table | safe }}

  <h2>Depth Coverage</h2>
  {{ depth_table | safe }}

  <h2>Visualizations</h2>
  <div class="figures">
    {% for fig in figures %}
    <div class="fig-card">
      <img src="{{ fig.rel_path }}" alt="{{ fig.name }}" loading="lazy"/>
      <div class="fig-caption">{{ fig.name }}</div>
    </div>
    {% endfor %}
  </div>

  <h2>Key Findings & Issues</h2>
  <ul>
    {% for finding in findings %}
    <li>{{ finding | safe }}</li>
    {% endfor %}
  </ul>

  <h2>Checkpoint 1 Status</h2>
  <div class="callout ok">
    ✅ Raw dataset audit complete. Awaiting user approval before Checkpoint 2 (flattening).
  </div>
</body>
</html>"""


def _df_to_html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, border=0, classes="", escape=True)


def write_html_report(
    schema_result: dict,
    dq: dict[str, pd.DataFrame],
    wc: dict[str, pd.DataFrame],
    figure_paths: list[Path],
    findings: list[str],
) -> Path:
    """Render and write the full HTML audit report."""
    arrow = schema_result["arrow_schema"]
    rc = wc["report_counts"]

    # Build schema tables
    schema_df = pd.DataFrame(arrow["columns"])
    nested_rows = []
    for col, info in schema_result["nested_columns"].items():
        nested_rows.append({
            "column": col,
            "total_nested_records": info["total_nested_records"],
            "nonempty_parent_rows": info["rows_with_nonempty_array"],
            "sub_fields": ", ".join(info["sub_fields"]) or "—",
        })
    nested_df = pd.DataFrame(nested_rows)

    # Coverage stats for summary cards
    nc = dq["nested_coverage"]
    activity_total = nc.loc[nc["column"] == "activity", "total_nested_records"].values
    fluid_total = nc.loc[nc["column"] == "fluid", "total_nested_records"].values

    # Figure references (relative to reports/)
    figs = []
    for p in figure_paths:
        if p.exists():
            figs.append({"rel_path": f"figures/{p.name}", "name": p.stem.replace("_", " ").title()})

    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(_HTML_TEMPLATE)
    html = tmpl.render(
        generated_at=_NOW,
        num_rows=f"{arrow['num_rows']:,}",
        num_cols=arrow["num_columns"],
        num_wellbores=len(rc),
        num_wells=rc["nameWell"].nunique(),
        date_min=str(rc["earliest_report"].min()),
        date_max=str(rc["latest_report"].max()),
        total_activity=f"{int(activity_total[0]):,}" if len(activity_total) else "—",
        total_fluid=f"{int(fluid_total[0]):,}" if len(fluid_total) else "—",
        schema_table=_df_to_html_table(schema_df),
        nested_table=_df_to_html_table(nested_df),
        dq_top_level_table=_df_to_html_table(dq["top_level"]),
        dq_statusinfo_table=_df_to_html_table(dq["statusinfo_sentinels"]),
        nested_coverage_table=_df_to_html_table(dq["nested_coverage"]),
        well_table=_df_to_html_table(rc),
        depth_table=_df_to_html_table(wc["depth_coverage"]),
        figures=figs,
        findings=findings,
    )

    path = REPORTS_DIR / "audit_report.html"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    log.info("Wrote HTML report: %s", path.name)
    return path


def write_all_reports(
    schema_result: dict,
    dq: dict[str, pd.DataFrame],
    wc: dict[str, pd.DataFrame],
    figure_paths: list[Path],
    findings: list[str],
) -> list[Path]:
    """Write all Checkpoint-1 reports. Returns list of written file paths."""
    log.info("=== REPORT WRITING START ===")
    written = [
        write_schema_report(schema_result),
        write_data_quality_report(dq),
        write_well_coverage_report(wc),
        write_html_report(schema_result, dq, wc, figure_paths, findings),
    ]
    log.info("=== REPORT WRITING COMPLETE: %d files written ===", len(written))
    return written
