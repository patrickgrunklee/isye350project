# Quick Start Guide

## Run All 10 DoH Scenarios

**Single command to do everything:**
```bash
python run_complete_analysis.py
```

This runs all 10 scenarios:
- (0,0), (1,3), (2,6), (3,8), (4,10), (5,12), (7,15), (9,17), (11,19), (14,21)

Output: `results/Phase2_DAILY/doh_sensitivity_summary.csv`

---

## Run Individual Scenario

```bash
# Example: Run 3 days international, 1 day domestic
python phase2_DAILY_parameterized.py --doh_intl 3 --doh_dom 1
```

---

## View Results

Results are saved in scenario-specific folders:
```
results/Phase2_DAILY/
├── 0_0_doh/expansion_requirements_0_0_doh.csv
├── 3_1_doh/expansion_requirements_3_1_doh.csv
├── 6_2_doh/expansion_requirements_6_2_doh.csv
...
└── doh_sensitivity_summary.csv  (comparison of all)
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `phase2_DAILY_parameterized.py` | Main model (accepts DoH parameters) |
| `run_complete_analysis.py` | **RUN THIS** - Does everything |
| `run_all_scenarios.py` | Batch runner for all scenarios |
| `generate_lead_time_files.py` | Creates Lead Time CSV files |
| `PARAMETERIZED_MODEL_README.md` | Full documentation |

---

## Model Features

✅ Daily time granularity (2,520 periods)
✅ 93% capacity constraint (Columbus: current, Sac/Austin: expansion only)
✅ Pallet limits: Sacramento 2,810, Austin 2,250
✅ Uniform demand distribution
✅ Inventory carryover
