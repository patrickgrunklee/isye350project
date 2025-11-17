# DoH Analysis System Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DoH SENSITIVITY ANALYSIS                        │
│                                                                         │
│  Two Analysis Modes: Main 10 Scenarios OR Full Matrix (100 scenarios)  │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐      ┌──────────────────────────────────┐
│   MAIN 10 SCENARIOS          │      │   FULL MATRIX (100 scenarios)    │
│   (Quick Analysis)           │      │   (Comprehensive Analysis)       │
├──────────────────────────────┤      ├──────────────────────────────────┤
│ • 10 strategic combinations  │      │ • All 100 combinations           │
│ • Runtime: ~30 minutes       │      │ • Runtime: ~5 hours              │
│ • Diagonal + key points      │      │ • Complete sensitivity map       │
└──────────────────────────────┘      └──────────────────────────────────┘
           │                                        │
           │                                        │
           ▼                                        ▼
┌──────────────────────────────┐      ┌──────────────────────────────────┐
│  run_complete_analysis.py    │      │ run_all_scenarios_FULL_MATRIX.py │
│                              │      │                                  │
│  Single command execution:   │      │  Single command execution:       │
│  1. Generate 10 lead files   │      │  1. Check/generate 100 lead files│
│  2. Run 10 scenarios         │      │  2. Run 100 scenarios            │
│  3. Create summary CSV       │      │  3. Auto-run analysis script     │
└──────────────────────────────┘      └──────────────────────────────────┘
           │                                        │
           └────────────────┬───────────────────────┘
                            │
                            ▼
           ┌────────────────────────────────────┐
           │  generate_lead_time_files.py       │
           │  OR                                │
           │  generate_lead_time_files_FULL_    │
           │  MATRIX.py                         │
           │                                    │
           │  Creates Lead Time CSV files with  │
           │  DoH values based on SKU type      │
           └────────────────────────────────────┘
                            │
                            ▼
           ┌────────────────────────────────────┐
           │     phase2_DAILY_parameterized.py  │
           │                                    │
           │  Core optimization model:          │
           │  • Accepts --doh_intl & --doh_dom  │
           │  • 2,520 daily time periods        │
           │  • 93% capacity utilization        │
           │  • Pallet expansion limits         │
           │  • Slack variables for violations  │
           └────────────────────────────────────┘
                            │
                            ▼
           ┌────────────────────────────────────┐
           │  Results stored in:                │
           │  results/Phase2_DAILY/{scenario}/  │
           │                                    │
           │  expansion_requirements_*.csv      │
           └────────────────────────────────────┘
                            │
                            ▼
           ┌────────────────────────────────────┐
           │  analyze_full_matrix_results.py    │
           │  (FULL MATRIX only)                │
           │                                    │
           │  Post-processing:                  │
           │  • Summary CSV                     │
           │  • Pivot tables (matrices)         │
           │  • Statistics (min/max/mean)       │
           └────────────────────────────────────┘
                            │
                            ▼
           ┌────────────────────────────────────┐
           │  Final Deliverables:               │
           │                                    │
           │  • doh_sensitivity_summary.csv     │
           │    (Main 10)                       │
           │  • doh_full_matrix_summary.csv     │
           │    (Full matrix - all 100)         │
           │  • doh_matrix_TOTAL_EXPANSION.csv  │
           │  • doh_matrix_SACRAMENTO.csv       │
           │  • doh_matrix_AUSTIN.csv           │
           └────────────────────────────────────┘
```

---

## File Reference Matrix

| File | Type | Purpose | When to Use |
|------|------|---------|-------------|
| **run_complete_analysis.py** | Runner | Main 10 scenarios end-to-end | Quick sensitivity check |
| **run_all_scenarios_FULL_MATRIX.py** | Runner | All 100 scenarios end-to-end | Comprehensive analysis |
| **run_all_scenarios.py** | Runner | Main 10 scenarios only (no lead gen) | If lead files exist |
| **generate_lead_time_files.py** | Generator | Create 10 lead time CSVs | Manual prep for main 10 |
| **generate_lead_time_files_FULL_MATRIX.py** | Generator | Create 100 lead time CSVs | Manual prep for full matrix |
| **phase2_DAILY_parameterized.py** | Core Model | Optimization engine | Called by runners |
| **analyze_full_matrix_results.py** | Analysis | Post-process 100 scenarios | After full matrix completes |
| **QUICK_START.md** | Docs | Quick reference guide | First-time users |
| **PARAMETERIZED_MODEL_README.md** | Docs | Detailed model documentation | Understanding parameters |
| **FULL_MATRIX_README.md** | Docs | Full matrix deep dive | Using all 100 scenarios |
| **HOW_TO_RUN_FULL_MATRIX.md** | Docs | Step-by-step full matrix | Running full analysis |
| **DOH_ANALYSIS_SYSTEM_OVERVIEW.md** | Docs | This file - system map | Understanding architecture |

---

## Decision Tree: Which Script to Run?

```
Do you need comprehensive DoH sensitivity analysis?
│
├─ NO → Want quick analysis of key scenarios?
│       │
│       └─ YES → Run: python run_complete_analysis.py
│                Time: ~30 minutes
│                Output: 10 scenarios, sensitivity_summary.csv
│
└─ YES → Want all 100 combinations for heatmap/optimization?
         │
         └─ YES → Run: python run_all_scenarios_FULL_MATRIX.py
                  Time: ~5 hours
                  Output: 100 scenarios, pivot tables, matrices

Need to re-run just the analysis on existing results?
└─ Run: python analyze_full_matrix_results.py
```

---

## DoH Value Sets

### Domestic DoH Values
```
[0, 1, 2, 3, 4, 5, 7, 9, 11, 14] days
```
Applies to: SKUA1-3, SKUT1-4, SKUD1-3, SKUC1-2

### International DoH Values
```
[0, 3, 6, 8, 10, 12, 15, 17, 19, 21] days
```
Applies to: SKUW1-3, SKUE1-3

### Main 10 Scenarios (Diagonal + Strategic Points)
```
(Domestic, International)
──────────────────────────
(0, 0)      - No safety stock
(1, 3)      - Minimal
(2, 6)      - Low
(3, 8)      - Medium-low
(4, 10)     - Medium
(5, 12)     - Medium-high
(7, 15)     - High
(9, 17)     - Very high
(11, 19)    - Extra high
(14, 21)    - Maximum
```

### Full Matrix (All Combinations)
```
10 domestic × 10 international = 100 scenarios

Example rows of the matrix:
International\Domestic  0    1    2    3    4    5    7    9   11   14
0                     0_0  0_1  0_2  0_3  0_4  0_5  0_7  0_9  0_11 0_14
3                     3_0  3_1  3_2  3_3  3_4  3_5  3_7  3_9  3_11 3_14
6                     6_0  6_1  6_2  6_3  6_4  6_5  6_7  6_9  6_11 6_14
...
21                   21_0 21_1 21_2 21_3 21_4 21_5 21_7 21_9 21_11 21_14
```

---

## Model Constraints (Applied to All Scenarios)

### Capacity Utilization (93%)
```
Columbus (cannot expand):
  shelves_used ≤ 0.93 × current_capacity

Sacramento & Austin (can expand):
  shelves_used ≤ current_capacity + 0.93 × expansion_shelves
```

### Pallet Expansion Limits
```
Sacramento: Max 2,810 pallet shelves
Austin:     Max 2,250 pallet shelves
```

### Slack Variables (Penalty Weights)
```
Demand violation:           1,000 (high penalty)
DoH violation:                 10 (medium)
Shelf capacity violation:     100 (medium-high)
Pallet expansion violation:   500 (high)
Volume violation:              50 (medium-low)
```

### Time Granularity
```
120 months × 21 business days = 2,520 daily time periods
Uniform demand distribution per day
```

---

## Output Structure

### Main 10 Scenarios Output
```
results/Phase2_DAILY/
├── 0_0_doh/expansion_requirements_0_0_doh.csv
├── 3_1_doh/expansion_requirements_3_1_doh.csv
├── 6_2_doh/expansion_requirements_6_2_doh.csv
├── 8_3_doh/expansion_requirements_8_3_doh.csv
├── 10_4_doh/expansion_requirements_10_4_doh.csv
├── 12_5_doh/expansion_requirements_12_5_doh.csv
├── 15_7_doh/expansion_requirements_15_7_doh.csv
├── 17_9_doh/expansion_requirements_17_9_doh.csv
├── 19_11_doh/expansion_requirements_19_11_doh.csv
├── 21_14_doh/expansion_requirements_21_14_doh.csv
└── doh_sensitivity_summary.csv
```

### Full Matrix Output (100 scenarios)
```
results/Phase2_DAILY/
├── 0_0_doh/expansion_requirements_0_0_doh.csv
├── 3_0_doh/expansion_requirements_3_0_doh.csv
├── 6_0_doh/expansion_requirements_6_0_doh.csv
├── ... (91 more scenario folders) ...
├── 21_14_doh/expansion_requirements_21_14_doh.csv
├── doh_full_matrix_summary.csv           ← All 100 in table
├── doh_matrix_TOTAL_EXPANSION.csv        ← 10×10 pivot table
├── doh_matrix_SACRAMENTO.csv             ← Sacramento only
└── doh_matrix_AUSTIN.csv                 ← Austin only
```

---

## Common Workflows

### Workflow 1: Quick Sensitivity Check
```bash
# Run main 10 scenarios
python run_complete_analysis.py

# Review summary
cat results/Phase2_DAILY/doh_sensitivity_summary.csv

# Identify trends
# → How does expansion change with DoH?
# → Which facility needs more expansion?
```

### Workflow 2: Find Optimal DoH Combination
```bash
# Run full matrix
python run_all_scenarios_FULL_MATRIX.py

# Open pivot table in Excel
# results/Phase2_DAILY/doh_matrix_TOTAL_EXPANSION.csv

# Apply conditional formatting (heatmap)
# → Find minimum expansion cell
# → Identify optimal (domestic, international) combination
```

### Workflow 3: Analyze Specific DoH Range
```bash
# Edit run_all_scenarios_FULL_MATRIX.py
# Modify domestic_values = [3, 4, 5]  # Focus on medium DoH
# Modify international_values = [10, 12, 15]  # Focus on medium-high

# Run subset
python run_all_scenarios_FULL_MATRIX.py

# Analyze subset results
python analyze_full_matrix_results.py
```

### Workflow 4: Re-run Failed Scenarios
```bash
# Check which scenarios completed
ls results/Phase2_DAILY/

# Manually run missing scenario
python phase2_DAILY_parameterized.py --doh_intl 12 --doh_dom 7

# Re-run analysis
python analyze_full_matrix_results.py
```

---

## Performance Considerations

| Scenario Count | Lead Time Gen | Optimization | Analysis | Total |
|----------------|---------------|--------------|----------|-------|
| 1 scenario     | ~1 second     | 2-4 minutes  | N/A      | ~3 min |
| 10 scenarios   | ~3 seconds    | 20-40 min    | ~1 sec   | ~30 min |
| 100 scenarios  | ~30 seconds   | 4-6 hours    | ~5 sec   | ~5 hours |

**Bottleneck:** Optimization solve time (GAMSPy LP solver)

**Recommendations:**
- Run main 10 scenarios first to verify system works
- Run full matrix overnight or during off-hours
- Use machine with 8GB+ RAM for large models
- Consider parallel processing for faster completion (requires code modification)

---

## Next Steps

**To get started:**

1. **Quick test (30 minutes):**
   ```bash
   python run_complete_analysis.py
   ```

2. **Full analysis (5 hours):**
   ```bash
   python run_all_scenarios_FULL_MATRIX.py
   ```

3. **Review results:**
   - Open `results/Phase2_DAILY/doh_matrix_TOTAL_EXPANSION.csv`
   - Find minimum expansion scenario
   - Analyze trade-offs

**For more details:**
- Quick start: `QUICK_START.md`
- Model parameters: `PARAMETERIZED_MODEL_README.md`
- Full matrix guide: `FULL_MATRIX_README.md`
- Step-by-step: `HOW_TO_RUN_FULL_MATRIX.md`
