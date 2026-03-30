"""
CPU Scheduling Algorithm Simulator
Implements: FCFS, SJF (Non-preemptive), SRT (Preemptive), Round Robin, MLFQ
"""

import csv
import json
from copy import deepcopy
from collections import deque


# ─────────────────────────────────────────
# Process data class
# ─────────────────────────────────────────
class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.priority = priority
        self.remaining = burst   # used by preemptive algorithms
        # metrics (filled after simulation)
        self.start_time = None
        self.finish_time = None
        self.waiting_time = None
        self.turnaround_time = None
        self.response_time = None

    def reset(self):
        """Reset runtime state for re-simulation."""
        self.remaining = self.burst
        self.start_time = None
        self.finish_time = None
        self.waiting_time = None
        self.turnaround_time = None
        self.response_time = None

    def __repr__(self):
        return f"Process(pid={self.pid}, arrival={self.arrival}, burst={self.burst})"


# ─────────────────────────────────────────
# Helper: compute metrics after simulation
# ─────────────────────────────────────────
def compute_metrics(processes):
    """
    Given processes with start_time and finish_time filled,
    compute waiting_time, turnaround_time, response_time.
    """
    for p in processes:
        p.turnaround_time = p.finish_time - p.arrival
        p.waiting_time = p.turnaround_time - p.burst
        p.response_time = p.start_time - p.arrival


def average_metrics(processes):
    n = len(processes)
    avg_wt = sum(p.waiting_time for p in processes) / n
    avg_tat = sum(p.turnaround_time for p in processes) / n
    avg_rt = sum(p.response_time for p in processes) / n
    return avg_wt, avg_tat, avg_rt


# ─────────────────────────────────────────
# 1. FCFS – First Come First Serve
# ─────────────────────────────────────────
def fcfs(processes):
    """
    Non-preemptive. Sort by arrival time; ties broken by PID.
    Returns a Gantt chart list of (pid, start, end) tuples.
    """
    procs = sorted(deepcopy(processes), key=lambda p: (p.arrival, p.pid))
    gantt = []
    time = 0

    for p in procs:
        if time < p.arrival:        # CPU idle gap
            gantt.append(("IDLE", time, p.arrival))
            time = p.arrival
        p.start_time = time
        time += p.burst
        p.finish_time = time
        gantt.append((p.pid, p.start_time, p.finish_time))

    compute_metrics(procs)
    return procs, gantt


# ─────────────────────────────────────────
# 2. SJF – Shortest Job First (Non-preemptive)
# ─────────────────────────────────────────
def sjf(processes):
    """
    Non-preemptive SJF.  At each decision point pick the
    available process with the smallest burst time.
    """
    procs = deepcopy(processes)
    done = []
    gantt = []
    time = 0
    remaining = list(procs)

    while remaining:
        # Processes that have arrived
        available = [p for p in remaining if p.arrival <= time]
        if not available:
            # Jump to next arrival (idle)
            next_arr = min(p.arrival for p in remaining)
            gantt.append(("IDLE", time, next_arr))
            time = next_arr
            available = [p for p in remaining if p.arrival <= time]

        # Pick shortest burst; tie-break by PID
        chosen = min(available, key=lambda p: (p.burst, p.pid))
        remaining.remove(chosen)
        chosen.start_time = time
        time += chosen.burst
        chosen.finish_time = time
        gantt.append((chosen.pid, chosen.start_time, chosen.finish_time))
        done.append(chosen)

    compute_metrics(done)
    return done, gantt


# ─────────────────────────────────────────
# 3. SRT – Shortest Remaining Time (Preemptive)
# ─────────────────────────────────────────
def srt(processes):
    """
    Preemptive version of SJF.  At every clock tick, the process
    with the shortest remaining burst is run.
    """
    procs = deepcopy(processes)
    for p in procs:
        p.remaining = p.burst

    gantt = []
    time = 0
    done = []
    n = len(procs)

    while len(done) < n:
        available = [p for p in procs if p.arrival <= time and p.finish_time is None]

        if not available:
            # Idle
            next_arr = min(p.arrival for p in procs if p.finish_time is None)
            if gantt and gantt[-1][0] == "IDLE":
                gantt[-1] = ("IDLE", gantt[-1][1], next_arr)
            else:
                gantt.append(("IDLE", time, next_arr))
            time = next_arr
            continue

        # Pick process with shortest remaining time; tie-break by pid
        chosen = min(available, key=lambda p: (p.remaining, p.pid))

        # Record first-start (response time)
        if chosen.start_time is None:
            chosen.start_time = time

        # Determine how long chosen runs before a preemption event
        # Preemption events: a new process arrives, or chosen finishes
        future_arrivals = [p.arrival for p in procs
                           if p.arrival > time and p.finish_time is None]
        if future_arrivals:
            next_event = min(future_arrivals)
            run_until = min(time + chosen.remaining, next_event)
        else:
            run_until = time + chosen.remaining

        run_time = run_until - time
        chosen.remaining -= run_time

        # Append to gantt (merge consecutive slices of same process)
        if gantt and gantt[-1][0] == chosen.pid:
            gantt[-1] = (chosen.pid, gantt[-1][1], run_until)
        else:
            gantt.append((chosen.pid, time, run_until))

        time = run_until

        if chosen.remaining == 0:
            chosen.finish_time = time
            done.append(chosen)

    compute_metrics(done)
    return done, gantt


# ─────────────────────────────────────────
# 4. Round Robin
# ─────────────────────────────────────────
def round_robin(processes, quantum=2):
    """
    Preemptive Round Robin with configurable time quantum.
    Uses a FIFO queue.  Newly arriving processes join the back
    of the queue when the current slice ends.
    """
    procs = deepcopy(processes)
    for p in procs:
        p.remaining = p.burst

    # Sort by arrival so we can add to queue in order
    sorted_procs = sorted(procs, key=lambda p: (p.arrival, p.pid))
    queue = deque()
    gantt = []
    time = 0
    idx = 0          # index into sorted_procs (next to arrive)
    done = []
    in_queue = set()

    # Seed queue with processes arriving at t=0
    while idx < len(sorted_procs) and sorted_procs[idx].arrival <= time:
        queue.append(sorted_procs[idx])
        in_queue.add(sorted_procs[idx].pid)
        idx += 1

    while queue or idx < len(sorted_procs):
        if not queue:
            # CPU idle until next arrival
            next_arr = sorted_procs[idx].arrival
            gantt.append(("IDLE", time, next_arr))
            time = next_arr
            while idx < len(sorted_procs) and sorted_procs[idx].arrival <= time:
                queue.append(sorted_procs[idx])
                in_queue.add(sorted_procs[idx].pid)
                idx += 1

        p = queue.popleft()

        if p.start_time is None:
            p.start_time = time

        run_time = min(quantum, p.remaining)
        p.remaining -= run_time
        end_time = time + run_time

        if gantt and gantt[-1][0] == p.pid:
            gantt[-1] = (p.pid, gantt[-1][1], end_time)
        else:
            gantt.append((p.pid, time, end_time))

        time = end_time

        # Enqueue new arrivals that arrived during this slice
        newly_arrived = []
        while idx < len(sorted_procs) and sorted_procs[idx].arrival <= time:
            newly_arrived.append(sorted_procs[idx])
            in_queue.add(sorted_procs[idx].pid)
            idx += 1

        if p.remaining > 0:
            # Re-queue current process after new arrivals
            for na in newly_arrived:
                queue.append(na)
            queue.append(p)
        else:
            p.finish_time = time
            done.append(p)
            for na in newly_arrived:
                queue.append(na)

    compute_metrics(done)
    return done, gantt


# ─────────────────────────────────────────
# 5. MLFQ – Multilevel Feedback Queue
# ─────────────────────────────────────────
def mlfq(processes, quantums=None, aging_threshold=10):
    """
    3-level MLFQ:
      Queue 0 (highest): RR q=quantums[0]
      Queue 1           : RR q=quantums[1]
      Queue 2 (lowest)  : FCFS (unlimited quantum)
    Demotion: process uses its full quantum → drops one level.
    Aging: a process waiting too long in a lower queue → promoted to Q0.
    """
    if quantums is None:
        quantums = [2, 4, float('inf')]

    procs = deepcopy(processes)
    for p in procs:
        p.remaining = p.burst
        p.queue_level = 0           # all start at top queue
        p.wait_since = p.arrival    # for aging

    sorted_procs = sorted(procs, key=lambda p: (p.arrival, p.pid))
    queues = [deque(), deque(), deque()]
    gantt = []
    time = 0
    idx = 0
    done = []

    def enqueue_arrivals():
        nonlocal idx
        while idx < len(sorted_procs) and sorted_procs[idx].arrival <= time:
            p = sorted_procs[idx]
            queues[0].append(p)
            idx += 1

    def apply_aging():
        """Promote starving processes (waiting too long) to queue 0."""
        for level in [1, 2]:
            promoted = []
            for p in list(queues[level]):
                if time - p.wait_since >= aging_threshold:
                    promoted.append(p)
            for p in promoted:
                queues[level].remove(p)
                p.queue_level = 0
                p.wait_since = time
                queues[0].append(p)

    enqueue_arrivals()

    while len(done) < len(procs):
        apply_aging()

        # Find highest-priority non-empty queue
        chosen_queue = None
        for lvl in range(3):
            if queues[lvl]:
                chosen_queue = lvl
                break

        if chosen_queue is None:
            # CPU idle
            if idx < len(sorted_procs):
                next_arr = sorted_procs[idx].arrival
                gantt.append(("IDLE", time, next_arr))
                time = next_arr
                enqueue_arrivals()
            continue

        p = queues[chosen_queue].popleft()

        if p.start_time is None:
            p.start_time = time

        q = quantums[chosen_queue]
        if q == float('inf'):
            run_time = p.remaining
        else:
            run_time = min(q, p.remaining)

        # Determine if a higher-priority process arrives mid-slice
        # (MLFQ allows preemption by new arrivals at queue 0)
        if idx < len(sorted_procs):
            next_arr = sorted_procs[idx].arrival
            actual_run = min(run_time, next_arr - time) if next_arr > time else run_time
        else:
            actual_run = run_time

        if actual_run <= 0:
            # New processes arrived; put p back and re-evaluate
            queues[chosen_queue].appendleft(p)
            enqueue_arrivals()
            continue

        p.remaining -= actual_run
        end_time = time + actual_run

        if gantt and gantt[-1][0] == p.pid:
            gantt[-1] = (p.pid, gantt[-1][1], end_time)
        else:
            gantt.append((p.pid, time, end_time))

        time = end_time
        enqueue_arrivals()

        if p.remaining == 0:
            p.finish_time = time
            done.append(p)
        else:
            used_full_quantum = (actual_run == run_time)
            if used_full_quantum and chosen_queue < 2:
                p.queue_level = chosen_queue + 1
            else:
                p.queue_level = chosen_queue
            p.wait_since = time
            queues[p.queue_level].append(p)

    compute_metrics(done)
    return done, gantt


# ─────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────
def print_gantt(gantt, title="Gantt Chart"):
    """Print a text-based Gantt chart."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

    # Top row: process labels
    bar = ""
    timeline = ""
    for (pid, start, end) in gantt:
        width = max((end - start) * 3, 4)
        label = str(pid) if pid == "IDLE" else f"P{pid}"
        bar += f"|{label.center(width)}"
        timeline += str(start).ljust(width + 1)
    bar += "|"
    timeline += str(gantt[-1][2])

    print(bar)
    print(timeline)


def print_metrics_table(processes, title="Process Metrics"):
    """Print a formatted table of scheduling metrics."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)
    header = f"{'PID':<6}{'Arrival':<10}{'Burst':<8}{'Start':<8}{'Finish':<9}{'WT':<6}{'TAT':<7}{'RT':<6}"
    print(header)
    print('-'*60)

    sorted_procs = sorted(processes, key=lambda p: p.pid)
    for p in sorted_procs:
        print(f"P{p.pid:<5}{p.arrival:<10}{p.burst:<8}{p.start_time:<8}"
              f"{p.finish_time:<9}{p.waiting_time:<6}{p.turnaround_time:<7}{p.response_time:<6}")

    avg_wt, avg_tat, avg_rt = average_metrics(processes)
    print('-'*60)
    print(f"{'AVERAGE':<43}{avg_wt:<6.2f}{avg_tat:<7.2f}{avg_rt:<6.2f}")


# ─────────────────────────────────────────
# Input helpers
# ─────────────────────────────────────────
def load_from_csv(path):
    """Load processes from a CSV file with columns: pid,arrival,burst,priority"""
    processes = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            processes.append(Process(
                pid=int(row['pid']),
                arrival=int(row['arrival']),
                burst=int(row['burst']),
                priority=int(row.get('priority', 0))
            ))
    return processes


def load_from_json(path):
    """Load processes from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return [Process(**p) for p in data]


def input_from_console():
    """Interactively input processes from the terminal."""
    n = int(input("Enter number of processes: "))
    processes = []
    for i in range(n):
        print(f"\nProcess {i+1}:")
        pid = int(input("  PID: "))
        arrival = int(input("  Arrival Time: "))
        burst = int(input("  Burst Time: "))
        priority = int(input("  Priority (0 if none): "))
        processes.append(Process(pid, arrival, burst, priority))
    return processes


# ─────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────
def run_all(processes, quantum=2, mlfq_quantums=None):
    """Run all 5 algorithms on the given process list and print results."""
    if mlfq_quantums is None:
        mlfq_quantums = [2, 4, float('inf')]

    algorithms = [
        ("FCFS",         lambda: fcfs(processes)),
        ("SJF",          lambda: sjf(processes)),
        ("SRT",          lambda: srt(processes)),
        (f"RR (q={quantum})", lambda: round_robin(processes, quantum)),
        ("MLFQ",         lambda: mlfq(processes, mlfq_quantums)),
    ]

    summary = []
    for name, algo in algorithms:
        result_procs, gantt = algo()
        print_gantt(gantt, title=f"{name} – Gantt Chart")
        print_metrics_table(result_procs, title=f"{name} – Metrics")
        avg_wt, avg_tat, avg_rt = average_metrics(result_procs)
        summary.append((name, avg_wt, avg_tat, avg_rt))

    # Comparative summary
    print(f"\n{'='*65}")
    print(" COMPARATIVE SUMMARY")
    print('='*65)
    print(f"{'Algorithm':<20}{'Avg WT':<12}{'Avg TAT':<12}{'Avg RT':<10}")
    print('-'*65)
    for name, wt, tat, rt in summary:
        print(f"{name:<20}{wt:<12.2f}{tat:<12.2f}{rt:<10.2f}")


if __name__ == "__main__":
    import sys

    # ── Sample scenario from project spec ──
    sample_processes = [
        Process(1, arrival=0, burst=5),
        Process(2, arrival=1, burst=3),
        Process(3, arrival=2, burst=8),
        Process(4, arrival=3, burst=6),
    ]

    if len(sys.argv) > 1:
        src = sys.argv[1]
        if src.endswith(".csv"):
            sample_processes = load_from_csv(src)
        elif src.endswith(".json"):
            sample_processes = load_from_json(src)
        elif src == "--console":
            sample_processes = input_from_console()

    quantum = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    run_all(sample_processes, quantum=quantum, mlfq_quantums=[2, 4, float('inf')])
