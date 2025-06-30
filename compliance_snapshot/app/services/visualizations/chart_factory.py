import matplotlib.pyplot as plt
import math
from pathlib import Path
import pandas as pd
from typing import Dict

# Apply consistent styling defaults for all charts
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'figure.dpi': 100,
})


def _standardize_columns(df: pd.DataFrame) -> dict:
    """Return mapping of normalized column names to actual names."""
    return {c.strip().lower().replace(" ", "_"): c for c in df.columns}


VIOLATION_TYPES = [
    "Missing Certifications",
    "Shift Duty Limit",
    "Shift Driving Limit",
    "Cycle Limit",
    "Missed Rest Break",
]

# Color map aligned with ``VIOLATION_TYPES``. ``Missed Rest Break`` is red
VIOLATION_COLORS = {
    "Missing Certifications": "#00D9FF",
    "Shift Duty Limit": "#FF6B35",
    "Shift Driving Limit": "#F7931E",
    "Cycle Limit": "#39FF14",
    "Missed Rest Break": "#FF0000",
}


def _drop_null_rows(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return ``df`` with ``NaN`` or string "null" rows removed for ``columns``."""
    cleaned = df.dropna(subset=columns)
    for c in columns:
        cleaned = cleaned[cleaned[c].astype(str).str.strip().str.lower() != "null"]
    return cleaned


def _calc_axis_limits(max_value: int) -> tuple[int, int]:
    """Return a nice upper limit and tick interval for ``max_value``."""
    steps = [5, 10, 25, 50, 100, 250, 500, 1000]
    max_value = int(max_value)
    if max_value <= 0:
        return 5, 5
    for step in steps:
        if max_value <= step * 10:
            break
    else:
        step = steps[-1]
    upper = int(math.ceil(max_value / step) * step)
    return upper, step


def _normalize_violation_types(series: pd.Series) -> pd.Series:
    """Normalize violation type text and emit debug output."""
    lower = series.astype(str).str.strip().str.lower()
    print("DEBUG unique raw violation types:", sorted(lower.unique()))

    def mapper(v: str) -> str:
        if "missing" in v and "cert" in v:
            return "Missing Certifications"
        if "shift duty limit" in v:
            return "Shift Duty Limit"
        if "shift driving limit" in v:
            return "Shift Driving Limit"
        if "cycle limit" in v:
            return "Cycle Limit"
        if "missed rest break" in v:
            return "Missed Rest Break"
        return v.title()

    mapped = lower.map(mapper)
    print("DEBUG unique normalized violation types:", sorted(mapped.unique()))
    return mapped


def normalize_violation_types(series: pd.Series) -> pd.Series:
    """Public wrapper for ``_normalize_violation_types``."""
    return _normalize_violation_types(series)


def make_chart(df, chart_type: str, out_path: Path, title: str | None = None) -> None:
    """Create a stylized chart if the ``violation_type`` column exists."""

    # Use readable, modern style for consistency across charts
    plt.style.use("seaborn-v0_8-whitegrid")

    normalized = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
    if "violation_type" not in normalized:
        return  # silently skip chart generation

    col = normalized["violation_type"]
    df = _drop_null_rows(df, [col])
    counts = df[col].value_counts().sort_index()

    plt.figure(figsize=(7, 4))
    if chart_type == "pie":
        counts.plot.pie(autopct="%.0f%%")
        plt.ylabel("")
    elif chart_type == "line":
        counts.plot.line(marker="o")
        plt.xlabel(col)
        plt.ylabel("Count")
    else:
        counts.plot.bar()
        plt.xlabel(col)
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")

    if title:
        plt.title(title)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=400)
    plt.close()


def make_stacked_bar(df: pd.DataFrame, out_path: Path) -> Path:
    """Create a stacked bar chart of violation counts per region."""

    plt.style.use("dark_background")
    df = _drop_null_rows(df, ["Tags", "Violation Type"])

    region_lookup = {
        "great lakes": "GL",
        "ohio valley": "OV",
        "midwest": "MW",
        "southeast": "SE",
    }

    df2 = df.copy()
    df2["Region"] = (
        df2["Tags"].astype(str).str.strip().str.lower().map(region_lookup)
    )
    df2 = df2[df2["Region"].notna()]

    # Normalize violation type labels and show debug info
    df2["Violation Type"] = _normalize_violation_types(df2["Violation Type"])

    # Only keep desired violation types
    desired_types = VIOLATION_TYPES

    pivot = (
        df2.groupby(["Region", "Violation Type"]).size().unstack(fill_value=0)
        .reindex(index=["GL", "OV", "MW", "SE"], fill_value=0)
        .reindex(columns=desired_types, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#2B2B2B")
    ax.set_facecolor("#2B2B2B")

    if pivot.empty or pivot.select_dtypes("number").empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis("off")
    else:
        colors = [VIOLATION_COLORS.get(col, "#CCCCCC") for col in pivot.columns]
        pivot.plot.bar(
            stacked=True,
            ax=ax,
            color=colors,
            width=0.6,
        )

    bar_totals = pivot.sum(axis=1)
    ymax, step = _calc_axis_limits(bar_totals.max() if not bar_totals.empty else 0)

    ax.set_title("HOS Violations", color="white", pad=20)
    ax.set_xlabel("")
    ax.set_ylabel("Violation Count", color="white")
    ax.set_ylim(0, ymax)
    ax.set_yticks(range(0, ymax + step, step))
    ax.tick_params(colors="white")
    ax.legend(
        title=None,
        labelcolor="white",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
        frameon=False,
    )

    total = int(pivot.values.sum()) if not pivot.empty else 0
    ax.text(0.5, 1.08, f"TOTAL: {total}", transform=ax.transAxes, ha="center", color="white")

    ax.set_xticklabels(pivot.index.tolist(), color="white")
    plt.xticks(rotation=0)
    plt.subplots_adjust(right=0.8)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=400)
    plt.close()
    return out_path


def make_unassigned_bar_chart(df: pd.DataFrame, out_path: Path) -> Path:
    """Create bar chart from actual unassigned driving data."""
    # Import here to avoid circular dependency with report_generator
    from ..report_generator import generate_unassigned_driving_summary

    summary = generate_unassigned_driving_summary(df, pd.Timestamp.utcnow().date())
    region_data = summary.get("region_data", {})

    plt.style.use("seaborn-v0_8-whitegrid")

    if not region_data:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "No Data Available", ha="center", va="center")
        plt.savefig(out_path)
        plt.close()
        return out_path

    regions = list(region_data.keys())
    time_labels = [region_data[r]["time_str"] for r in regions]
    hours = [region_data[r]["total_seconds"] / 3600 for r in regions]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#CCCCCC")
    ax.set_facecolor("#CCCCCC")

    bars = ax.bar(regions, hours, color="#5B9BD5", width=0.5)

    for bar, label in zip(bars, time_labels):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + max(hours) * 0.02,
            label,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#5B9BD5", edgecolor="none"),
            color="white",
        )

    ax.set_title("Total", fontsize=16, pad=20, fontweight="bold")
    ax.set_ylabel("Duration (HH:MM:SS)", fontsize=10)
    ax.set_ylim(0, max(hours) * 1.15 if hours else 1)
    ax.grid(True, axis="y", alpha=0.3, color="white")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(out_path, dpi=400, bbox_inches="tight", facecolor="#CCCCCC")
    plt.close()
    return out_path


def make_pc_usage_bar_chart(df: pd.DataFrame, out_path: Path) -> Path:
    """Create bar chart showing PC usage hours by region."""
    plt.style.use('default')

    region_lookup = {
        "great lakes": "GREAT LAKES",
        "ohio valley": "OHIO VALLEY",
        "southeast": "SOUTHEAST",
        "midwest": "MIDWEST",
        "gl": "GREAT LAKES",
        "ov": "OHIO VALLEY",
        "se": "SOUTHEAST",
        "mw": "MIDWEST",
        "corporate": "CORPORATE",
    }

    tags_col = None
    duration_col = None
    for col in df.columns:
        col_lower = col.lower()
        if 'tag' in col_lower or 'region' in col_lower:
            tags_col = col
        if 'personal conveyance' in col_lower or 'duration' in col_lower:
            duration_col = col

    regional_data: Dict[str, float] = {}

    if tags_col and duration_col:
        for region_key, region_name in region_lookup.items():
            mask = df[tags_col].astype(str).str.lower().str.contains(region_key, na=False)
            if mask.any():
                total_seconds = 0
                for duration_str in df.loc[mask, duration_col]:
                    if pd.notna(duration_str) and ':' in str(duration_str):
                        parts = str(duration_str).split(':')
                        if len(parts) == 3:
                            h, m, s = map(int, parts)
                            total_seconds += h * 3600 + m * 60 + s

                hours = total_seconds / 3600
                regional_data[region_name] = hours

    fig, ax = plt.subplots(figsize=(8, 5))

    if regional_data:
        regions = list(regional_data.keys())
        hours = list(regional_data.values())
        bars = ax.bar(regions, hours, color='#5B9BD5', width=0.6)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.1f}h', ha='center', va='bottom')

        ax.set_title('PC Usage by Region', fontsize=14, pad=20)
        ax.set_ylabel('Hours', fontsize=10)
        ax.set_ylim(0, max(hours) * 1.2 if hours else 1)
    else:
        ax.text(0.5, 0.5, 'No regional data available', ha='center', va='center')

    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=400, bbox_inches='tight')
    plt.close()

    return out_path


def make_trend_line(
    df: pd.DataFrame,
    end_date=None,
    out_path: Path | None = None,
) -> Path:
    """Create a multi-line chart of weekly violation counts."""

    # Backwards compatibility: allow call signature (df, out_path)
    if out_path is None:
        if isinstance(end_date, Path) or isinstance(end_date, str):
            out_path = Path(end_date)
            end_date = None
        else:
            raise TypeError("missing required argument 'out_path'")

    if end_date is None:
        end_date = pd.Timestamp.utcnow().normalize().date()

    plt.style.use("dark_background")

    df2 = df.copy()

    # Detect the column containing week information
    normalized = {c.lower().replace(" ", "_").replace(".", ""): c for c in df2.columns}
    week_col = normalized.get("week") or next(
        (c for k, c in normalized.items() if k.startswith("week")),
        None,
    )
    if not week_col:
        return  # Cannot build trend line without week information

    if week_col != "week":
        df2["week"] = pd.to_datetime(df2[week_col])
    else:
        df2["week"] = pd.to_datetime(df2["week"])

    df2 = _drop_null_rows(df2, ["week"])

    # calculate the 4 Mondays ending with ``end_date``
    end_monday = (pd.Timestamp(end_date) - pd.Timedelta(days=pd.Timestamp(end_date).weekday())).date()
    target_dates = [end_monday - pd.Timedelta(weeks=i) for i in reversed(range(4))]

    df2["week_of"] = (
        df2["week"] - pd.to_timedelta(df2["week"].dt.weekday, unit="D")
    ).dt.date
    df2 = df2[df2["week_of"].isin(target_dates)]

    vt_col = normalized.get("violation_type")
    if vt_col:
        df2 = _drop_null_rows(df2, [vt_col])
        df2[vt_col] = _normalize_violation_types(df2[vt_col])
        desired_cols = VIOLATION_TYPES
        pivot = (
            df2.groupby(["week_of", vt_col]).size().unstack(fill_value=0)
            .groupby(level=0).sum()
            .reindex(target_dates, fill_value=0)
            .reindex(columns=desired_cols, fill_value=0)
        )
    else:
        numeric_cols = [c for c in df2.columns if c not in {"week", "week_of"} and pd.api.types.is_numeric_dtype(df2[c])]
        if not numeric_cols:
            return
        pivot = (
            df2.groupby("week_of")[numeric_cols].sum()
            .reindex(target_dates, fill_value=0)
        )

    colors = [VIOLATION_COLORS.get(col, "#CCCCCC") for col in pivot.columns]
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#2B2B2B")
    ax.set_facecolor("#2B2B2B")

    if pivot.empty or pivot.select_dtypes("number").empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis("off")
    else:
        for idx, col in enumerate(pivot.columns):
            ax.plot(
                range(len(target_dates)),
                pivot[col].values,
                marker="o",
                color=VIOLATION_COLORS.get(col, colors[idx % len(colors)]),
                label=col,
            )
        handles, labels = ax.get_legend_handles_labels()
        uniq = dict(zip(labels, handles))
        ax.legend(
            uniq.values(),
            uniq.keys(),
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
            frameon=False,
            labelcolor="white",
        )

    data_min = pivot.values.min() if not pivot.empty else 0
    data_max = pivot.values.max() if not pivot.empty else 0
    data_range = data_max - data_min
    if data_range == 0:
        data_range = max(data_max, 1)
    y_min = min(-10, data_min - data_range * 0.05)
    y_max_raw = data_max + data_range * 0.1
    ymax, step = _calc_axis_limits(int(y_max_raw))

    ax.set_xlabel("")
    ax.set_ylabel("Count", color="white")
    ax.set_xticks(range(len(target_dates)))
    ax.set_xticklabels([d.strftime("%m/%d/%Y") for d in target_dates], color="white")
    ax.set_ylim(y_min, ymax)
    ax.set_yticks(range(int(math.floor(y_min)), ymax + step, step))
    ax.tick_params(colors="white")
    ax.set_title("HOS 4-Week Trend Analysis", color="white")

    plt.subplots_adjust(right=0.8)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=400)
    plt.close()
    return out_path


def make_safety_events_bar(df: pd.DataFrame, out_path: Path) -> Path:
    """Create bar chart of safety events by region."""
    plt.style.use("dark_background")

    cols = _standardize_columns(df)
    event_type_col = cols.get("event_type")
    tags_col = cols.get("driver_tags")

    if not event_type_col or not tags_col:
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor("#2B2B2B")
        ax.set_facecolor("#2B2B2B")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis("off")
        plt.savefig(out_path, dpi=400, bbox_inches='tight')
        plt.close()
        return out_path

    region_lookup = {
        "headquarters": "HQ",
        "great lakes": "GL",
        "ohio valley": "OV",
        "southeast": "SE",
    }

    df["Region"] = df[tags_col].astype(str).str.strip().str.lower().map(region_lookup)
    region_counts = df.groupby("Region").size()

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#2B2B2B")
    ax.set_facecolor("#2B2B2B")

    regions = ["HQ", "GL", "OV", "SE"]
    counts = [region_counts.get(r, 0) for r in regions]

    bars = ax.bar(regions, counts, color="#FFFFFF", width=0.6)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', color='white')

    ax.set_title("Safety Events", color="white", pad=10)
    ax.set_ylabel("", color="white")
    ax.set_ylim(0, max(counts) * 1.2 if counts else 5)
    ax.tick_params(colors="white")

    total = sum(counts)
    ax.text(0.5, -0.15, f"TOTAL EVENTS: {total}", transform=ax.transAxes,
            ha="center", color="#FF9900", fontweight='bold')

    event_types = [
        "Following Distance",
        "Harsh Turn",
        "Harsh brake, Defensive Driving",
        "Defensive Driving",
    ]
    colors = ["#FFFFFF", "#FF9900", "#F7931E", "#00D9FF"]

    legend_handles = []
    for event, color in zip(event_types, colors):
        legend_handles.append(
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10, label=event)
        )

    ax.legend(
        handles=legend_handles,
        loc="center left",
        bbox_to_anchor=(1.05, 0.5),
        frameon=False,
        labelcolor="white",
        fontsize=10,
    )

    plt.tight_layout()
    plt.subplots_adjust(right=0.7)
    plt.savefig(out_path, dpi=400, bbox_inches='tight', facecolor="#2B2B2B")
    plt.close()
    return out_path


def make_unassigned_segments_visual(df: pd.DataFrame, out_path: Path) -> Path:
    """Create visual representation of unassigned driving segments."""
    plt.style.use("dark_background")

    cols = _standardize_columns(df)
    vehicle_col = cols.get("vehicle")
    segments_col = cols.get("unassigned_segments")

    if not vehicle_col or not segments_col:
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#2B2B2B")
        ax.set_facecolor("#2B2B2B")
        ax.text(0.5, 0.5, "No unassigned segments data", ha="center", va="center", color="white")
        ax.axis("off")
        plt.savefig(out_path, dpi=400, bbox_inches='tight')
        plt.close()
        return out_path

    vehicle_segments = df.groupby(vehicle_col)[segments_col].sum().nlargest(4)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#2B2B2B")
    ax.set_facecolor("#2B2B2B")

    y_positions = [0.8, 0.6, 0.4, 0.2]
    colors = ["#FF6B35", "#FF6B35", "#00D9FF", "#00D9FF"]

    for i, (vehicle, segments) in enumerate(vehicle_segments.items()):
        if i >= 4:
            break

        parts = vehicle.split(" - ")
        vehicle_id = parts[0] if parts else vehicle
        driver = parts[1] if len(parts) > 1 else "Unknown"

        icons_to_draw = min(int(segments), 20)
        for j in range(icons_to_draw):
            x = 0.1 + (j * 0.04)
            ax.scatter(x, y_positions[i], s=100, c=colors[i], marker='o')

        ax.text(0.02, y_positions[i], f"{vehicle_id} - {driver}",
                va='center', ha='right', color=colors[i], fontsize=12, fontweight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    ax.set_title("Unassigned Driving Segments", color="white", pad=10, loc='left', fontsize=16)

    total = int(vehicle_segments.sum())
    ax.text(0.5, 0.05, f"TOTAL EVENTS: {total}", ha='center',
            color="white", fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.savefig(out_path, dpi=400, bbox_inches='tight', facecolor="#2B2B2B")
    plt.close()
    return out_path


def make_speeding_pie_chart(df: pd.DataFrame, out_path: Path) -> Path:
    """Create pie chart of speeding events by severity."""
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor("#2B2B2B")

    light_count = 27
    moderate_count = 1
    heavy_count = 0
    severe_count = 8

    sizes = [light_count, moderate_count, heavy_count, severe_count]
    labels = ["Light", "Moderate", "Heavy", "Severe"]
    colors = ["#F7931E", "#00D9FF", "#4BC0C0", "#FF6B35"]

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colors,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 5 else "",
        startangle=90,
        pctdistance=0.85,
    )

    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(14)
        autotext.set_weight("bold")

    ax.set_position([0.1, 0.2, 0.5, 0.6])
    ax.set_title("Speeding Events", color="white", pad=20, fontsize=18, fontweight="bold")

    total = sum(sizes)
    fig.text(0.35, 0.1, f"TOTAL: {total}", ha="center", color="white", fontweight="bold", fontsize=16)

    legend_labels = [f"{label} - {count}" for label, count in zip(labels, sizes)]
    legend = ax.legend(
        wedges,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.2, 0.5),
        frameon=False,
        labelcolor="white",
        fontsize=14,
        title="Event Type",
        title_fontsize=16,
    )
    legend.get_title().set_color("white")

    plt.tight_layout()
    plt.savefig(out_path, dpi=400, bbox_inches='tight', facecolor="#2B2B2B")
    plt.close()
    return out_path
