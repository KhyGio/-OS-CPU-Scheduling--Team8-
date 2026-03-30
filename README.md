# -OS-CPU-Scheduling--Team8-
# OS-CPU-Scheduling scheduler.py          # Python CLI simulator (all 5 algorithms)
sample_processes.csv  # Sample input (CSV format)
README.md
```

---

## Setup & Installation

### Python Simulator
**Requirements:** Python 3.7+  (no external libraries needed)

```bash
# Clone the repo
git clone https://github.com/yourteam/OS-CPU-Scheduling-Team1
cd OS-CPU-Scheduling-Team1

# Run with built-in sample scenario
python scheduler.py

# Run with CSV input, custom quantum
python scheduler.py sample_processes.csv 2

# Run with JSON input
python scheduler.py sample_processes.json

# Run with manual console input
python scheduler.py --console
```

### Web UI
Open `index.html` in any modern browser ] | Per-queue quantums |
| `aging_threshold` | 10 | Ticks before a starving process is promoted |

---

## CSV Input Format

```csv
pid,arrival,burst,priority
1,0,5,0
2,1,3,0
3,2,8,0
4,3,6,0
```

## JSON Input Format

```json
[
 {"pid": 1, "arrival": 0, "burst": 5, "priority": 0},
 {"pid": 2, "arrival": 1, "burst": 3, "priority": 0}
]
```