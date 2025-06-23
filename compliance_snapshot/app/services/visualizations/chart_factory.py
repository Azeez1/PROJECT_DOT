import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd


def make_chart(df, chart_type: str, out_path: Path, title: str | None = None) -> None:
    """Create a stylized chart if the ``violation_type`` column exists."""

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


def make_stacked_bar(df: pd.DataFrame, out_path: Path) -> None:
    """Create a stacked bar chart of violation counts per region."""
    plt.style.use("seaborn-v0_8-whitegrid")
    pivot = df.pivot_table(
        index="Tags",
        columns="Violation Type",
        aggfunc="size",
        fill_value=0,
    )
    ax = pivot.plot.bar(stacked=True, figsize=(7, 4))
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def make_trend_line(df: pd.DataFrame, out_path: Path) -> None:
    """Create a line chart of weekly violation counts."""
    plt.style.use("seaborn-v0_8-whitegrid")
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
    ax = pivot.plot.line(marker="o", figsize=(7, 4))
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
