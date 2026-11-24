"""Підсумок і графіки за результатами Locust + monitor.py.

python loadtest/analyze.py summary  <prefix> [monitor.csv]
python loadtest/analyze.py timeline <prefix> <monitor.csv> <out.png> <title>
python loadtest/analyze.py compare  <out_prefix> label=prefix [label=prefix ...]
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


def load_stats(prefix: str) -> pd.Series:
    df = pd.read_csv(f"{prefix}_stats.csv")
    return df[df["Name"] == "Aggregated"].iloc[0]


def summary(prefix: str, monitor: str | None = None, warmup: float = 20.0) -> dict:
    s = load_stats(prefix)
    total = int(s["Request Count"])
    failed = int(s["Failure Count"])
    result = {
        "requests": total,
        "rps": round(float(s["Requests/s"]), 1),
        "avg_ms": round(float(s["Average Response Time"]), 1),
        "min_ms": round(float(s["Min Response Time"]), 1),
        "max_ms": round(float(s["Max Response Time"]), 1),
        "p50_ms": int(s["50%"]),
        "p95_ms": int(s["95%"]),
        "p99_ms": int(s["99%"]),
        "error_rate_pct": round(100 * failed / total, 3) if total else 0.0,
    }
    if monitor and Path(monitor).exists():
        m = pd.read_csv(monitor)
        m = m[m["t_sec"] >= warmup]
        result.update(
            sys_cpu_avg=round(m["sys_cpu_pct"].mean(), 1),
            sys_cpu_max=round(m["sys_cpu_pct"].max(), 1),
            sys_mem_avg=round(m["sys_mem_pct"].mean(), 1),
            sys_mem_max=round(m["sys_mem_pct"].max(), 1),
            app_cpu_avg=round(m["app_cpu_pct"].mean(), 1),
            app_rss_mb_max=round(m["app_rss_mb"].max(), 1),
            pg_cpu_avg=round(m["postgres_cpu_pct"].mean(), 1),
            redis_rss_mb_max=round(m["redis_rss_mb"].max(), 1),
        )
    return result


def timeline(prefix: str, monitor: str, out: str, title: str) -> None:
    h = pd.read_csv(f"{prefix}_stats_history.csv")
    h = h[h["Name"] == "Aggregated"].copy()
    h["t"] = h["Timestamp"] - h["Timestamp"].iloc[0]
    m = pd.read_csv(monitor)

    fig, ax = plt.subplots(2, 2, figsize=(12, 7))
    ax[0, 0].plot(h["t"], h["Requests/s"], color="#1f77b4")
    ax[0, 0].set(title="Пропускна здатність (RPS)", xlabel="с", ylabel="запитів/с")
    ax[0, 1].plot(h["t"], h["50%"], label="медіана", color="#2ca02c")
    ax[0, 1].plot(h["t"], h["95%"], label="95-й перцентиль", color="#d62728")
    ax[0, 1].set(title="Затримка", xlabel="с", ylabel="мс")
    ax[0, 1].legend()
    ax[1, 0].plot(m["t_sec"], m["sys_cpu_pct"], label="CPU система, %")
    ax[1, 0].plot(m["t_sec"], m["app_cpu_pct"], label="CPU застосунок, %")
    ax[1, 0].plot(m["t_sec"], m["postgres_cpu_pct"], label="CPU PostgreSQL, %")
    ax[1, 0].set(title="Завантаження CPU", xlabel="с", ylabel="%")
    ax[1, 0].legend()
    ax[1, 1].plot(
        m["t_sec"], m["app_rss_mb"], label="RAM застосунок, МБ", color="#1f77b4"
    )
    ax[1, 1].plot(m["t_sec"], m["redis_rss_mb"], label="RAM Redis, МБ", color="#2ca02c")
    ax[1, 1].set(title="Використання RAM", xlabel="с", ylabel="МБ")
    twin = ax[1, 1].twinx()
    twin.plot(
        m["t_sec"], m["sys_mem_pct"], label="RAM система, %", color="#d62728", ls="--"
    )
    twin.set_ylabel("% від усієї пам'яті")
    twin.set_ylim(0, max(10, m["sys_mem_pct"].max() * 1.5))
    lines = ax[1, 1].get_lines() + twin.get_lines()
    ax[1, 1].legend(lines, [ln.get_label() for ln in lines], loc="center right")
    for a in ax.flat:
        a.grid(alpha=0.3)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=130)


def compare(out_prefix: str, pairs: list[str]) -> None:
    labels, data = [], []
    for pair in pairs:
        label, prefix = pair.split("=", 1)
        labels.append(label)
        data.append(summary(prefix))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    colors = ["#7f7f7f", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"][: len(labels)]
    bars = ax[0].bar(labels, [d["rps"] for d in data], color=colors)
    ax[0].set(title="Пропускна здатність (RPS)", ylabel="запитів/с")
    ax[0].bar_label(bars, fmt="%.0f")
    x = range(len(labels))
    w = 0.38
    b1 = ax[1].bar(
        [i - w / 2 for i in x],
        [d["avg_ms"] for d in data],
        w,
        label="середня",
        color="#2ca02c",
    )
    b2 = ax[1].bar(
        [i + w / 2 for i in x],
        [d["p95_ms"] for d in data],
        w,
        label="95-й перцентиль",
        color="#d62728",
    )
    ax[1].set_xticks(list(x), labels)
    ax[1].set(title="Затримка", ylabel="мс")
    ax[1].bar_label(b1, fmt="%.0f")
    ax[1].bar_label(b2, fmt="%.0f")
    ax[1].legend()
    for a in ax:
        a.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.png", dpi=130)
    print(
        json.dumps(dict(zip(labels, data, strict=True)), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "summary":
        print(
            json.dumps(
                summary(sys.argv[2], *(sys.argv[3:4])), ensure_ascii=False, indent=2
            )
        )
    elif cmd == "timeline":
        timeline(*sys.argv[2:6])
    elif cmd == "compare":
        compare(sys.argv[2], sys.argv[3:])
