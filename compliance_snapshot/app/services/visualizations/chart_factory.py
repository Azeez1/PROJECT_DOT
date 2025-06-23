import matplotlib.pyplot as plt
from pathlib import Path


def make_chart(df, chart_type: str, out_path: Path):
    counts = df["violation_type"].value_counts()
    plt.figure(figsize=(6, 3))
    if chart_type == "pie":
        counts.plot.pie(autopct="%.0f%%")
    elif chart_type == "line":
        counts.plot.line(marker="o")
    else:
        counts.plot.bar()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
