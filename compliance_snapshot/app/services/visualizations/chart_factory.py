import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd


def make_chart(df, chart_type: str, out_path: Path, title: str | None = None) -> None:
    """Create a stylized chart if the ``violation_type`` column exists.

    Parameters
    ----------
    df:
        DataFrame containing the data.
    chart_type:
        ``"bar"``, ``"line"`` or ``"pie"``.
    out_path:
        Path where the PNG should be written.
    title:
        Optional chart title. If omitted the table name is used.
    """

    # Use readable, modern style for consistency across charts
    plt.style.use("seaborn-v0_8-whitegrid")

    normalized = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
    if "violation_type" not in normalized:
        return  # silently skip chart generation

    col = normalized["violation_type"]
    counts = df[col].value_counts()

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


<<<<<< codex/add-manual-trend-end-date-control
def make_trend_line(df, out_path: Path, title: str | None = None) -> None:
    """Create a simple line chart showing counts per week."""
    plt.style.use("seaborn-v0_8-whitegrid")
    counts = df.groupby("week").size().sort_index()

    plt.figure(figsize=(7, 4))
    counts.plot.line(marker="o")
    plt.xlabel("Week")
    plt.ylabel("Count")
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
=======
def make_stacked_bar(df, out_path: Path):
    """Create stacked bar chart of violation counts per region."""
    pivot = df.pivot_table(
        index="Tags",
        columns="Violation Type",
        aggfunc="size",
        fill_value=0,
    )
    ax = pivot.plot.bar(stacked=True, figsize=(6, 3))
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def make_trend_line(df, out_path: Path):
    """Create line chart of weekly violation counts."""
    df2 = df.copy()
    df2["week"] = pd.to_datetime(df2["WEEK OF..."])
    pivot = (
        df2.pivot_table(
            index="week",
            columns="Violation Type",
            aggfunc="size",
            fill_value=0,
        )
        .sort_index()
    )
    ax = pivot.plot.line(marker="o", figsize=(6, 3))
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
>>>>>> main
    plt.close()
