"""Збір системних метрик (CPU/RAM) під час тесту в CSV.

Запуск:  python loadtest/monitor.py results/run.csv [інтервал_сек]
Зупинка: Ctrl+C або SIGTERM.
"""

import csv
import signal
import sys
import time

import psutil

GROUPS = {
    "app": ("uvicorn",),
    "postgres": ("postgres",),
    "redis": ("redis-server",),
    "nginx": ("nginx",),
    "locust": ("locust",),
}


def procs_of(keys):
    found = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            text = " ".join(p.info["cmdline"] or []) + " " + (p.info["name"] or "")
            if any(k in text for k in keys):
                found.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def main() -> None:
    out = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    cache = {name: {} for name in GROUPS}
    psutil.cpu_percent(None)
    start = time.time()
    with open(out, "w", newline="") as fh:
        writer = csv.writer(fh)
        header = ["t_sec", "sys_cpu_pct", "sys_mem_pct"]
        for name in GROUPS:
            header += [f"{name}_cpu_pct", f"{name}_rss_mb"]
        writer.writerow(header)
        while running:
            time.sleep(interval)
            row = [
                round(time.time() - start, 1),
                psutil.cpu_percent(None),
                psutil.virtual_memory().percent,
            ]
            for name, keys in GROUPS.items():
                cpu = rss = 0.0
                for p in procs_of(keys):
                    try:
                        proc = cache[name].setdefault(p.pid, p)
                        cpu += proc.cpu_percent(None)
                        rss += proc.memory_full_info().pss / 1_048_576
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                row += [round(cpu, 1), round(rss, 1)]
            writer.writerow(row)
            fh.flush()


if __name__ == "__main__":
    main()
