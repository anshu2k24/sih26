"""
ertmac.audit.visualizations
=============================
Generate all Checkpoint-1 plots and save them as high-resolution PNGs.

Every function:
- Saves to FIGURES_DIR / <filename>.png (300 dpi)
- Returns the saved Path for use in the HTML report
- Has clear titles, axis labels with units, and legends where needed
- Uses a consistent visual style
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for reproducibility
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from ertmac.utils.logging_setup import get_logger
from ertmac.utils.paths import FIGURES_DIR

log = get_logger(__name__)

# ── Global style ─────────────────────────────────────────────────────────────
sns.set_theme(style="darkgrid", context="talk", palette="muted")
plt.rcParams.update(
    {
        "figure.facecolor": "#1e1e2e",
        "axes.facecolor": "#2a2a3e",
        "axes.edgecolor": "#555577",
        "axes.labelcolor": "#cdd6f4",
        "xtick.color": "#cdd6f4",
        "ytick.color": "#cdd6f4",
        "text.color": "#cdd6f4",
        "grid.color": "#44475a",
        "legend.framealpha": 0.4,
        "legend.facecolor": "#1e1e2e",
        "legend.edgecolor": "#555577",
    }
)

ACCENT = "#89b4fa"
PALETTE = ["#89b4fa", "#a6e3a1", "#fab387", "#f38ba8", "#cba6f7",
           "#89dceb", "#f9e2af", "#eba0ac", "#b4befe", "#94e2d5"]
DPI = 300


def _save(fig: plt.Figure, name: str) -> Path:
    """Save a figure and close it. Returns the saved path."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / name
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Saved plot: %s", out.name)
    return out


# ── Plot 1: Report counts by wellbore ────────────────────────────────────────
def plot_report_counts(report_counts_df: pd.DataFrame) -> Path:
    df = report_counts_df.sort_values("report_count", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(df["nameWellbore"], df["report_count"], color=ACCENT)
    ax.bar_label(bars, padding=4, fontsize=10, color="#cdd6f4")
    ax.set_xlabel("Number of Daily Drilling Reports", fontsize=13)
    ax.set_ylabel("Wellbore", fontsize=13)
    ax.set_title("Daily Drilling Reports per Wellbore\n(Volve Field, Equinor Open Dataset)", fontsize=14, pad=12)
    fig.tight_layout()
    return _save(fig, "01_report_counts_per_wellbore.png")


# ── Plot 2: Timeline gantt-style ──────────────────────────────────────────────
def plot_timeline(report_counts_df: pd.DataFrame) -> Path:
    df = report_counts_df.copy()
    df["earliest_report"] = pd.to_datetime(df["earliest_report"])
    df["latest_report"] = pd.to_datetime(df["latest_report"])
    df = df.sort_values("earliest_report")

    fig, ax = plt.subplots(figsize=(14, 9))
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]

    for i, (_, row) in enumerate(df.iterrows()):
        ax.barh(
            i,
            (row["latest_report"] - row["earliest_report"]).days,
            left=row["earliest_report"],
            color=colours[i],
            height=0.6,
            alpha=0.85,
        )
        ax.text(
            row["latest_report"],
            i,
            f"  {row['report_count']}",
            va="center",
            fontsize=9,
            color="#cdd6f4",
        )

    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["nameWellbore"], fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.set_xlabel("Year", fontsize=13)
    ax.set_title("Drilling Activity Timeline per Wellbore\n(label = DDR count)", fontsize=14, pad=12)
    fig.tight_layout()
    return _save(fig, "02_drilling_timeline.png")


# ── Plot 3: Nested array coverage ─────────────────────────────────────────────
def plot_nested_coverage(nested_coverage_df: pd.DataFrame) -> Path:
    df = nested_coverage_df.copy()
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: % rows with data
    ax = axes[0]
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["column"], df["nonempty_pct"], color=colours)
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=10, color="#cdd6f4")
    ax.set_xlim(0, 115)
    ax.set_xlabel("Parent Rows with ≥1 Nested Record (%)", fontsize=12)
    ax.set_title("Nested Column Coverage\n(% of 1,759 reports with data)", fontsize=13)

    # Right: total nested records
    ax2 = axes[1]
    bars2 = ax2.barh(df["column"], df["total_nested_records"], color=colours)
    ax2.bar_label(bars2, fmt="%d", padding=4, fontsize=10, color="#cdd6f4")
    ax2.set_xlabel("Total Nested Records (all reports combined)", fontsize=12)
    ax2.set_title("Total Nested Records per Column", fontsize=13)

    fig.suptitle("Nested Array Columns — Coverage and Volume", fontsize=15, y=1.01)
    fig.tight_layout()
    return _save(fig, "03_nested_array_coverage.png")


# ── Plot 4: Sentinel / null heatmap for statusInfo fields ─────────────────────
def plot_statusinfo_missingness(sentinels_df: pd.DataFrame) -> Path:
    df = sentinels_df.copy()
    df["missing_pct"] = df["sentinel_pct"] + df["null_pct"]
    df["valid_pct"] = 100 - df["missing_pct"]
    df = df.sort_values("missing_pct", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 8))
    x = np.arange(len(df))
    w = 0.4
    b1 = ax.bar(x - w / 2, df["sentinel_pct"], width=w, label="Sentinel (-999.99)", color="#f38ba8")
    b2 = ax.bar(x + w / 2, df["null_pct"], width=w, label="NULL", color="#fab387")
    ax.set_xticks(x)
    ax.set_xticklabels([f.replace("statusInfo.", "") for f in df["field"]], rotation=45, ha="right", fontsize=10)
    ax.set_ylabel("Percentage of Nested Records (%)", fontsize=12)
    ax.set_title("statusInfo Fields — Sentinel & NULL Rate\n(sentinel = '-999.99', not a real measurement)", fontsize=13)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 110)
    fig.tight_layout()
    return _save(fig, "04_statusinfo_sentinel_null_rates.png")


# ── Plot 5: Max MD per wellbore ───────────────────────────────────────────────
def plot_depth_distribution(depth_df: pd.DataFrame) -> Path:
    df = depth_df.dropna(subset=["max_md_m"]).sort_values("max_md_m", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["nameWellbore"], df["max_md_m"], color=colours, label="Max MD (m)")
    ax.barh(df["nameWellbore"], df["max_tvd_m"].fillna(0), color="#a6e3a1", alpha=0.6, label="Max TVD (m)")
    ax.bar_label(bars, fmt="%.0f m", padding=4, fontsize=9, color="#cdd6f4")
    ax.set_xlabel("Depth (m)", fontsize=13)
    ax.set_title("Maximum Measured Depth (MD) and True Vertical Depth (TVD) per Wellbore", fontsize=13)
    ax.legend(fontsize=11)
    fig.tight_layout()
    return _save(fig, "05_max_depth_per_wellbore.png")


# ── Plot 6: Activity distribution ─────────────────────────────────────────────
def plot_activity_distribution(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        WITH u AS (SELECT UNNEST(activity) AS act FROM '{parquet_path}')
        SELECT act.proprietaryCode AS code, COUNT(*) AS cnt
        FROM u
        WHERE act.proprietaryCode IS NOT NULL
        GROUP BY code ORDER BY cnt DESC LIMIT 15
    """).df()
    con.close()

    df = df.sort_values("cnt", ascending=True)
    fig, ax = plt.subplots(figsize=(14, 8))
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["code"], df["cnt"], color=colours)
    ax.bar_label(bars, padding=4, fontsize=10, color="#cdd6f4")
    ax.set_xlabel("Number of Activity Records", fontsize=13)
    ax.set_title("Top 15 Drilling Activity Codes\n(from unnested activity[] records)", fontsize=13)
    fig.tight_layout()
    return _save(fig, "06_top15_activity_codes.png")


# ── Plot 7: Mud / fluid types ─────────────────────────────────────────────────
def plot_fluid_types(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        WITH u AS (SELECT UNNEST(fluid) AS fl FROM '{parquet_path}')
        SELECT fl.type AS mud_type, COUNT(*) AS cnt
        FROM u WHERE fl.type IS NOT NULL
        GROUP BY mud_type ORDER BY cnt DESC LIMIT 15
    """).df()
    con.close()

    df = df.sort_values("cnt", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["mud_type"], df["cnt"], color=colours)
    ax.bar_label(bars, padding=4, fontsize=10, color="#cdd6f4")
    ax.set_xlabel("Number of Fluid Records", fontsize=13)
    ax.set_title("Drilling Fluid / Mud Types\n(from unnested fluid[] records)", fontsize=13)
    fig.tight_layout()
    return _save(fig, "07_fluid_types.png")


# ── Plot 8: Lithology distribution ───────────────────────────────────────────
def plot_lithology(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        WITH u AS (SELECT UNNEST(lithShowInfo) AS l FROM '{parquet_path}')
        SELECT l.lithology AS lith, COUNT(*) AS cnt
        FROM u WHERE l.lithology IS NOT NULL
        GROUP BY lith ORDER BY cnt DESC LIMIT 15
    """).df()
    con.close()

    if df.empty:
        log.warning("No lithology data available; skipping lithology plot.")
        return FIGURES_DIR / "08_lithology_distribution.png"

    df = df.sort_values("cnt", ascending=True)
    fig, ax = plt.subplots(figsize=(13, 7))
    colours = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["lith"], df["cnt"], color=colours)
    ax.bar_label(bars, padding=4, fontsize=10, color="#cdd6f4")
    ax.set_xlabel("Number of Lithology Records", fontsize=13)
    ax.set_title("Lithology Distribution\n(from unnested lithShowInfo[] records)", fontsize=13)
    fig.tight_layout()
    return _save(fig, "08_lithology_distribution.png")


# ── Plot 9: Reports per year ──────────────────────────────────────────────────
def plot_reports_per_year(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        SELECT
            YEAR(CAST(dTimStart AS TIMESTAMPTZ)) AS yr,
            COUNT(*) AS report_count
        FROM '{parquet_path}'
        GROUP BY yr ORDER BY yr
    """).df()
    con.close()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(df["yr"], df["report_count"], color=ACCENT, width=0.7)
    ax.set_xlabel("Year", fontsize=13)
    ax.set_ylabel("Number of Daily Drilling Reports", fontsize=13)
    ax.set_title("Daily Drilling Reports Filed per Year\n(all wellbores combined)", fontsize=13)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    return _save(fig, "09_reports_per_year.png")


# ── Plot 10: Pore pressure EMW distribution ───────────────────────────────────
def plot_pore_pressure(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        WITH u AS (SELECT UNNEST(porePressure) AS pp FROM '{parquet_path}')
        SELECT
            TRY_CAST(pp.equivalentMudWeight AS DOUBLE) AS emw,
            TRY_CAST(pp.md AS DOUBLE) AS md
        FROM u
        WHERE TRY_CAST(pp.equivalentMudWeight AS DOUBLE) IS NOT NULL
          AND TRY_CAST(pp.equivalentMudWeight AS DOUBLE) > 0
          AND TRY_CAST(pp.equivalentMudWeight AS DOUBLE) < 3
    """).df()
    con.close()

    if df.empty:
        log.warning("No valid pore-pressure EMW data; skipping plot.")
        return FIGURES_DIR / "10_pore_pressure_emw.png"

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    axes[0].hist(df["emw"].dropna(), bins=40, color=ACCENT, edgecolor="#1e1e2e")
    axes[0].set_xlabel("Equivalent Mud Weight (g/cm³ or SG)", fontsize=12)
    axes[0].set_ylabel("Count", fontsize=12)
    axes[0].set_title("Pore Pressure EMW Distribution", fontsize=13)

    sc = axes[1].scatter(df["emw"], df["md"], alpha=0.35, s=15, c=df["emw"],
                         cmap="coolwarm")
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Equivalent Mud Weight (g/cm³ or SG)", fontsize=12)
    axes[1].set_ylabel("Measured Depth (m)", fontsize=12)
    axes[1].set_title("Pore Pressure EMW vs Depth", fontsize=13)
    fig.colorbar(sc, ax=axes[1], label="EMW")

    fig.tight_layout()
    return _save(fig, "10_pore_pressure_emw.png")


# ── Plot 11: Survey inclination & azimuth ─────────────────────────────────────
def plot_survey_trajectory(parquet_path: Path) -> Path:
    con = duckdb.connect()
    df = con.execute(f"""
        WITH u AS (
            SELECT nameWellbore, UNNEST(surveyStation) AS ss FROM '{parquet_path}'
        )
        SELECT
            nameWellbore,
            TRY_CAST(ss.md   AS DOUBLE) AS md,
            TRY_CAST(ss.tvd  AS DOUBLE) AS tvd,
            TRY_CAST(ss.incl AS DOUBLE) AS incl,
            TRY_CAST(ss.azi  AS DOUBLE) AS azi
        FROM u
        WHERE TRY_CAST(ss.md AS DOUBLE) IS NOT NULL
          AND TRY_CAST(ss.incl AS DOUBLE) IS NOT NULL
    """).df()
    con.close()

    if df.empty:
        log.warning("No survey data; skipping trajectory plot.")
        return FIGURES_DIR / "11_survey_trajectory.png"

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Inclination vs MD
    wells = df["nameWellbore"].unique()
    wcolours = {w: PALETTE[i % len(PALETTE)] for i, w in enumerate(wells)}
    for w, g in df.groupby("nameWellbore"):
        g_sorted = g.sort_values("md")
        axes[0].plot(g_sorted["incl"], g_sorted["md"], alpha=0.7,
                     lw=1.2, color=wcolours[w], label=w)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Inclination (°)", fontsize=12)
    axes[0].set_ylabel("Measured Depth (m)", fontsize=12)
    axes[0].set_title("Inclination vs Depth\n(per wellbore)", fontsize=13)

    # MD vs TVD
    for w, g in df.dropna(subset=["tvd"]).groupby("nameWellbore"):
        g_sorted = g.sort_values("md")
        axes[1].plot(g_sorted["md"], g_sorted["tvd"], alpha=0.7,
                     lw=1.2, color=wcolours[w], label=w)
    axes[1].set_xlabel("Measured Depth (m)", fontsize=12)
    axes[1].set_ylabel("True Vertical Depth (m)", fontsize=12)
    axes[1].set_title("MD vs TVD\n(per wellbore)", fontsize=13)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4,
               fontsize=8, bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout()
    return _save(fig, "11_survey_trajectory.png")


# ── Plot 12: Top-level null heatmap ──────────────────────────────────────────
def plot_top_level_nulls(top_level_df: pd.DataFrame) -> Path:
    df = top_level_df.copy().set_index("column")
    fig, ax = plt.subplots(figsize=(10, 6))
    values = df[["null_pct", "sentinel_pct"]].values
    im = ax.imshow(values.T, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df.index, rotation=45, ha="right", fontsize=10)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Null %", "Sentinel %"], fontsize=11)
    for i in range(len(df)):
        for j, key in enumerate(["null_pct", "sentinel_pct"]):
            val = df.iloc[i][key]
            ax.text(i, j, f"{val:.1f}%", ha="center", va="center",
                    fontsize=9, color="white" if val > 50 else "#1e1e2e")
    plt.colorbar(im, ax=ax, label="Percentage (%)")
    ax.set_title("Top-Level Column Missingness Heatmap\n(Null % and Sentinel '-999.99' %)", fontsize=13)
    fig.tight_layout()
    return _save(fig, "12_top_level_null_heatmap.png")


# ── Master function ───────────────────────────────────────────────────────────
def run_all_visualizations(
    parquet_path: Path,
    report_counts_df: pd.DataFrame,
    nested_coverage_df: pd.DataFrame,
    sentinels_df: pd.DataFrame,
    depth_df: pd.DataFrame,
    top_level_df: pd.DataFrame,
) -> list[Path]:
    """Generate all Checkpoint-1 plots.

    Returns
    -------
    List of paths to saved PNG files.
    """
    log.info("=== VISUALIZATION GENERATION START ===")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    tasks = [
        ("report counts", lambda: plot_report_counts(report_counts_df)),
        ("timeline", lambda: plot_timeline(report_counts_df)),
        ("nested coverage", lambda: plot_nested_coverage(nested_coverage_df)),
        ("statusInfo sentinels", lambda: plot_statusinfo_missingness(sentinels_df)),
        ("depth distribution", lambda: plot_depth_distribution(depth_df)),
        ("activity distribution", lambda: plot_activity_distribution(parquet_path)),
        ("fluid types", lambda: plot_fluid_types(parquet_path)),
        ("lithology", lambda: plot_lithology(parquet_path)),
        ("reports per year", lambda: plot_reports_per_year(parquet_path)),
        ("pore pressure", lambda: plot_pore_pressure(parquet_path)),
        ("survey trajectory", lambda: plot_survey_trajectory(parquet_path)),
        ("top-level nulls", lambda: plot_top_level_nulls(top_level_df)),
    ]

    for name, fn in tasks:
        try:
            path = fn()
            saved.append(path)
        except Exception as exc:
            log.error("Failed to generate plot '%s': %s", name, exc, exc_info=True)

    log.info("=== VISUALIZATION COMPLETE: %d plots saved ===", len(saved))
    return saved
