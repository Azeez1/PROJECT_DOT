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


def make_stacked_bar(df: pd.DataFrame, out_path: Path):
    """Create a stacked bar chart of violation counts per region."""

    plt.style.use("seaborn-v0_8-whitegrid")
    df = _drop_null_rows(df, ["Tags", "Violation Type"])

    regions = [
        ("Ohio Valley", "OV"),
        ("Great Lakes", "GL"),
        ("Midwest", "MW"),
        ("Southeast", "SE"),
    ]

    frames: list[pd.DataFrame] = []
    for region, key in regions:
        mask = df["Tags"].astype(str).str.contains(key, case=False, na=False)
        sub = df[mask].copy()
        if not sub.empty:
            sub["Region"] = region
            frames.append(sub)

    if frames:
        df2 = pd.concat(frames, ignore_index=True)
    else:
        df2 = pd.DataFrame(columns=["Region", "Violation Type"])

    pivot = (
        df2.pivot_table(
            index="Region",
            columns="Violation Type",
            aggfunc="size",
            fill_value=0,
        )
        .reindex([r[0] for r in regions], fill_value=0)
    )

    ax = pivot.plot.bar(stacked=True, figsize=(6, 3))
    ax.set_title("HOS Violations")
    ax.set_xlabel("")
    ax.set_ylabel("Violation Count")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path


def make_trend_line(df: pd.DataFrame, end_date=None, out_path: Path | None = None):
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

    plt.style.use("seaborn-v0_8-whitegrid")

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

    target_dates = []
    for i in reversed(range(4)):
        d = end_date - pd.Timedelta(days=7 * i)
        d = (pd.Timestamp(d) - pd.Timedelta(days=pd.Timestamp(d).weekday())).date()
        target_dates.append(d)

    df2["week_of"] = (df2["week"] - pd.to_timedelta(df2["week"].dt.weekday, unit="D")).dt.date
    df2 = df2[df2["week_of"].isin(target_dates)]

    vt_col = normalized.get("violation_type")
    if vt_col:
        df2 = _drop_null_rows(df2, [vt_col])
        pivot = (
            df2.pivot_table(
                index="week_of",
                columns=vt_col,
                aggfunc="size",
                fill_value=0,
            )
            .reindex(target_dates, fill_value=0)
            .sort_index(axis=1)
        )
    else:
        numeric_cols = [c for c in df2.columns if c not in {"week", "week_of"} and pd.api.types.is_numeric_dtype(df2[c])]
        if not numeric_cols:
            return
        pivot = (
            df2.groupby("week_of")[numeric_cols].sum()
            .reindex(target_dates, fill_value=0)
        )

    colors = plt.cm.tab10.colors
    ax = pivot.plot.line(marker="o", figsize=(7, 4), color=colors[: len(pivot.columns)])
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    ax.set_xticks(range(len(target_dates)))
    ax.set_xticklabels([d.strftime("%m/%d/%Y") for d in target_dates])
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path
