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
    pivot = df.pivot_table(
        index="Tags",            # OV / GL / SE on X-axis
        columns="Violation Type",
        aggfunc="size",
        fill_value=0,
    )

    ax = pivot.plot.bar(stacked=True, figsize=(6, 3))
    ax.set_title("HOS Violations by Region Tag")
    ax.set_xlabel("Region Tags (OV / GL / SE)")
    ax.set_ylabel("Violation Count")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path


def make_trend_line(df: pd.DataFrame, out_path: Path):
    """Create a line chart of weekly violation counts.

    The function is resilient to variations in the week column name and
    will plot one line per ``Violation Type`` or, if that column is not
    available, one line for each numeric column in ``df``.
    """

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

    # Determine which columns to plot. Prefer ``Violation Type`` if present.
    vt_col = normalized.get("violation_type")
    if vt_col:
        df2 = _drop_null_rows(df2, [vt_col])
        pivot = (
            df2.pivot_table(
                index="week",
                columns=vt_col,
                aggfunc="size",
                fill_value=0,
            )
            .sort_index()
            .sort_index(axis=1)
        )
    else:
        numeric_cols = [c for c in df2.columns if c != "week" and pd.api.types.is_numeric_dtype(df2[c])]
        if not numeric_cols:
            return
        pivot = df2.set_index("week")[numeric_cols]

    colors = plt.cm.tab10.colors
    ax = pivot.plot.line(marker="o", figsize=(7, 4), color=colors[: len(pivot.columns)])
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path
