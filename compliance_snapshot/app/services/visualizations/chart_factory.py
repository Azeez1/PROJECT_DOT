import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd


def _drop_null_rows(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return ``df`` with ``NaN`` or string "null" rows removed for ``columns``."""
    cleaned = df.dropna(subset=columns)
    for c in columns:
        cleaned = cleaned[cleaned[c].astype(str).str.strip().str.lower() != "null"]
    return cleaned


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

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def make_stacked_bar(df: pd.DataFrame, out_path: Path) -> Path:
    """Create a stacked bar chart of violation counts per region."""

    plt.style.use("dark_background")
    df = _drop_null_rows(df, ["Tags", "Violation Type"])

    # --- normalize regions to GL, OV, SE only ---
    regions = ["GL", "OV", "SE"]
    region_map = {abbr: abbr for abbr in regions}

    df2 = pd.DataFrame(columns=["Region", "Violation Type"])
    for abbr in regions:
        mask = df["Tags"].astype(str).str.contains(abbr, case=False, na=False)
        sub = df[mask].copy()
        if not sub.empty:
            sub["Region"] = region_map[abbr]
            df2 = pd.concat([df2, sub], ignore_index=True)

    # Normalize violation type labels
    vt_aliases = {
        "missing certifications": "Missing Certifications",
        "missing certification": "Missing Certifications",
        "shift duty limit": "Shift Duty Limit",
        "shift driving limit": "Shift Driving Limit",
        "cycle limit": "Cycle Limit",
    }
    df2["Violation Type"] = (
        df2["Violation Type"].astype(str).str.strip().str.lower().map(vt_aliases).fillna(df2["Violation Type"])
    )

    # Only keep desired violation types
    desired_types = [
        "Missing Certifications",
        "Shift Duty Limit",
        "Shift Driving Limit",
        "Cycle Limit",
    ]

    pivot = (
        df2.pivot_table(
            index="Region",
            columns="Violation Type",
            aggfunc="size",
            fill_value=0,
        )
        .reindex(regions, fill_value=0)
        .reindex(columns=desired_types, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor("#333333")
    ax.set_facecolor("#333333")

    if pivot.empty or pivot.select_dtypes("number").empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis("off")
    else:
        colors = ["#00bcd4", "#ff8c00", "#ffff00", "#808080"]
        pivot.plot.bar(
            stacked=True,
            ax=ax,
            color=colors[: len(pivot.columns)],
            width=0.6,
        )

    ax.set_title("HOS Violations", color="white")
    ax.set_xlabel("")
    ax.set_ylabel("Violation Count", color="white")
    ax.set_ylim(0, 120)
    ax.set_yticks(range(0, 121, 20))
    ax.tick_params(colors="white")
    ax.legend(title=None, labelcolor="white")

    total = int(pivot.values.sum()) if not pivot.empty else 0
    ax.text(0.5, 1.05, f"Total {total}", transform=ax.transAxes, ha="center", color="white")

    plt.xticks(rotation=0, color="white")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
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
        vt_aliases = {
            "missing certifications": "Missing Certifications",
            "missing certification": "Missing Certifications",
            "shift duty limit": "Shift Duty Limit",
            "shift driving limit": "Shift Driving Limit",
            "cycle limit": "Cycle Limit",
        }
        df2[vt_col] = (
            df2[vt_col].astype(str).str.strip().str.lower().map(vt_aliases).fillna(df2[vt_col])
        )
        pivot = (
            df2.pivot_table(
                index="week_of",
                columns=vt_col,
                aggfunc="size",
                fill_value=0,
            )
            .reindex(target_dates, fill_value=0)
            .reindex(columns=list(vt_aliases.values()), fill_value=0)
        )
    else:
        numeric_cols = [c for c in df2.columns if c not in {"week", "week_of"} and pd.api.types.is_numeric_dtype(df2[c])]
        if not numeric_cols:
            return
        pivot = (
            df2.groupby("week_of")[numeric_cols].sum()
            .reindex(target_dates, fill_value=0)
        )

    colors = ["#00bcd4", "#ff8c00", "#ffff00", "#808080"]
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("#333333")
    ax.set_facecolor("#333333")

    if pivot.empty or pivot.select_dtypes("number").empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis("off")
    else:
        for idx, col in enumerate(pivot.columns):
            ax.plot(
                range(len(target_dates)),
                pivot[col].values,
                marker="o",
                color=colors[idx % len(colors)],
                label=col,
            )

    ax.set_xlabel("")
    ax.set_ylabel("Count", color="white")
    ax.set_xticks(range(len(target_dates)))
    ax.set_xticklabels([d.strftime("%m/%d/%Y") for d in target_dates], color="white")
    ax.set_ylim(0, 200)
    ax.set_yticks(range(0, 201, 50))
    ax.tick_params(colors="white")
    ax.legend(loc="upper left", frameon=False, labelcolor="white")
    ax.set_title("HOS 4-Week Trend Analysis", color="white")

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path
