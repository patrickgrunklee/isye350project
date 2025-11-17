# Parameterized Daily Model Usage Guide

## Overview

Instead of maintaining separate files for each DoH scenario, use **`phase2_DAILY_parameterized.py`** - a single model that accepts DoH parameters.

## Benefits

✅ **Single source of truth** - One model file, easier maintenance
✅ **Consistent constraints** - All scenarios use identical logic
✅ **Easy to add scenarios** - No code duplication
✅ **Batch execution** - Run multiple scenarios automatically

## Current Scenarios (10 Total)

| # | Domestic DoH | International DoH | Scenario Name |
|---|--------------|-------------------|---------------|
| 1 | 0 days | 0 days | 0_0_doh |
| 2 | 1 day | 3 days | 3_1_doh |
| 3 | 2 days | 6 days | 6_2_doh |
| 4 | 3 days | 8 days | 8_3_doh |
| 5 | 4 days | 10 days | 10_4_doh |
| 6 | 5 days | 12 days | 12_5_doh |
| 7 | 7 days | 15 days | 15_7_doh |
| 8 | 9 days | 17 days | 17_9_doh |
| 9 | 11 days | 19 days | 19_11_doh |
| 10 | 14 days | 21 days | 21_14_doh |

---

## Quick Start (Easiest Method)

Run **everything** with one command:
```bash
python run_complete_analysis.py
```

This will:
1. ✅ Generate all 10 Lead Time CSV files automatically
2. ✅ Run all 10 scenarios
3. ✅ Create a comparison summary report

---

## Usage Options

### Option 1: Command Line Arguments (Quickest)

```bash
# Run 3/1 DoH scenario
python phase2_DAILY_parameterized.py --doh_intl 3 --doh_dom 1

# Run 5/2 DoH scenario
python phase2_DAILY_parameterized.py --doh_intl 5 --doh_dom 2

# Run with custom scenario name and time limit
python phase2_DAILY_parameterized.py --doh_intl 10 --doh_dom 3 --scenario_name "high_safety_stock" --max_time 300
```

### Option 2: JSON Config File

1. Create a config file (e.g., `my_scenario.json`):
```json
{
  "doh_international": 7,
  "doh_domestic": 2,
  "scenario_name": "7_2_doh",
  "max_solve_time": 180
}
```

2. Run with config:
```bash
python phase2_DAILY_parameterized.py --config my_scenario.json
```

### Option 3: Batch Run Multiple Scenarios

Run all scenarios at once:
```bash
python run_all_scenarios.py
```

Edit `run_all_scenarios.py` to add/remove scenarios:
```python
scenarios = [
    {"doh_intl": 0, "doh_dom": 0, "name": "0_0_doh"},
    {"doh_intl": 3, "doh_dom": 1, "name": "3_1_doh"},
    {"doh_intl": 5, "doh_dom": 2, "name": "5_2_doh"},
    {"doh_intl": 10, "doh_dom": 3, "name": "10_3_doh"},
    # Add your new scenarios here:
    {"doh_intl": 7, "doh_dom": 2, "name": "7_2_doh"},
    {"doh_intl": 14, "doh_dom": 5, "name": "14_5_doh"},
]
```

---

## Command Line Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--doh_intl` | int | Yes* | Days on hand for international SKUs |
| `--doh_dom` | int | Yes* | Days on hand for domestic SKUs |
| `--config` | str | Yes* | Path to JSON config file |
| `--scenario_name` | str | No | Custom name for output folder (default: `{doh_intl}_{doh_dom}_doh`) |
| `--max_time` | int | No | Max solve time in seconds (default: 180) |

*Either provide both `--doh_intl` and `--doh_dom`, OR provide `--config`

---

## Output Structure

Results are saved to scenario-specific directories:
```
results/Phase2_DAILY/
├── 0_0_doh/
│   └── expansion_requirements_0_0_doh.csv
├── 3_1_doh/
│   └── expansion_requirements_3_1_doh.csv
├── 5_2_doh/
│   └── expansion_requirements_5_2_doh.csv
└── 10_3_doh/
    └── expansion_requirements_10_3_doh.csv
```

---

## Adding New DoH Scenarios

### Step 1: Create Lead Time File

Create a new CSV file with your DoH values:
```
Model Data/Lead TIme_{intl}_{dom}_business_days.csv
```

Example: For 7 days international, 2 days domestic:
```
Model Data/Lead TIme_7_2_business_days.csv
```

The file should have:
- Column: `Columbus - Days on Hand` = 7 for international SKUs, 2 for domestic
- Column: `Sacramento - Days on Hand` = 7 for international SKUs, 2 for domestic
- Column: `Austin Days on Hand` = 7 for international SKUs, 2 for domestic

### Step 2: Run the Model

```bash
python phase2_DAILY_parameterized.py --doh_intl 7 --doh_dom 2
```

### Step 3: Add to Batch Script (Optional)

Edit `run_all_scenarios.py` and add your scenario:
```python
{"doh_intl": 7, "doh_dom": 2, "name": "7_2_doh"},
```

---

## Model Features

All scenarios include:
- ✅ 93% capacity constraint (Columbus: current capacity, Sacramento/Austin: expansion only)
- ✅ Pallet expansion limits (Sacramento: 2,810, Austin: 2,250)
- ✅ Daily time granularity (2,520 time periods)
- ✅ Uniform demand distribution
- ✅ Inventory carryover between days/months
- ✅ Truckload tracking (if enabled)

---

## Comparison of Old vs. New Approach

### Old Approach ❌
```
phase2_DAILY_0_0_doh.py    (1,046 lines)
phase2_DAILY_3_1_doh.py    (1,046 lines)
phase2_DAILY_5_2_doh.py    (1,046 lines)
phase2_DAILY_10_3_doh.py   (1,046 lines)
```
**Total: 4 files, ~4,200 lines**
- Hard to maintain (change must be copied to 4 files)
- Easy to introduce inconsistencies

### New Approach ✅
```
phase2_DAILY_parameterized.py  (1 file, ~600 lines)
run_all_scenarios.py           (batch script)
```
**Total: 2 files, ~650 lines**
- Single source of truth
- Guaranteed consistency
- Easy to add scenarios

---

## Troubleshooting

**Error: "Lead time file not found"**
```
ERROR: Lead time file not found: Model Data/Lead TIme_7_2_business_days.csv
```
→ Create the lead time CSV file with your DoH values (see Step 1 above)

**Error: "Must provide either --config or both --doh_intl and --doh_dom"**
```
ERROR: Must provide either --config or both --doh_intl and --doh_dom
```
→ Provide command line arguments: `python phase2_DAILY_parameterized.py --doh_intl 3 --doh_dom 1`

---

## Migration from Old Files

The old scenario-specific files (`phase2_DAILY_3_1_doh.py`, etc.) can remain for reference but **use the parameterized model for all new runs**.

To verify equivalence:
```bash
# Run old model
python phase2_DAILY_3_1_doh.py

# Run new model
python phase2_DAILY_parameterized.py --doh_intl 3 --doh_dom 1

# Compare results - should be identical
```
