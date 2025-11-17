# Full DoH Matrix Analysis Guide

## Overview

This guide explains how to run the **complete DoH sensitivity matrix** covering all 100 combinations of domestic and international days-on-hand values.

## Matrix Structure

**Domestic DoH values:** [0, 1, 2, 3, 4, 5, 7, 9, 11, 14] (10 values)
**International DoH values:** [0, 3, 6, 8, 10, 12, 15, 17, 19, 21] (10 values)

**Total scenarios:** 10 × 10 = **100 scenarios**

### Scenario Naming Convention

Format: `{international}_{domestic}_doh`

Examples:
- `0_0_doh` - 0 days international, 0 days domestic
- `21_14_doh` - 21 days international, 14 days domestic
- `10_3_doh` - 10 days international, 3 days domestic

## Quick Start: Run Full Matrix

**Single command to run everything:**

```bash
python run_all_scenarios_FULL_MATRIX.py
```

This will:
1. Generate all 100 Lead Time CSV files automatically
2. Run all 100 optimization scenarios
3. Create comprehensive analysis with pivot tables

**Estimated time:** ~5 hours (3 minutes per scenario × 100 scenarios)

The script includes a confirmation prompt before starting due to the long runtime.

---

## Step-by-Step Process

### Step 1: Generate Lead Time Files (Optional - Done Automatically)

If you want to pre-generate Lead Time files separately:

```bash
python generate_lead_time_files_FULL_MATRIX.py
```

This creates 100 CSV files in `Model Data/`:
```
Lead TIme_0_0_business_days.csv
Lead TIme_3_0_business_days.csv
Lead TIme_6_0_business_days.csv
...
Lead TIme_21_14_business_days.csv
```

### Step 2: Run All 100 Scenarios

```bash
python run_all_scenarios_FULL_MATRIX.py
```

Progress will be displayed:
```
================================================================================
RUNNING FULL DOH MATRIX - ALL 100 SCENARIOS
================================================================================

WARNING: This will run 100 optimization scenarios (10 domestic × 10 international)
Estimated time: ~300 minutes (5 hours) at 3 minutes per scenario

Do you want to continue? (yes/no): yes

Starting full matrix run...

[1/100] Running scenario 0_0_doh (International: 0, Domestic: 0)...
✓ Completed in 180 seconds

[2/100] Running scenario 0_1_doh (International: 0, Domestic: 1)...
✓ Completed in 175 seconds
...
```

### Step 3: Analyze Results

After all scenarios complete, run the analysis script:

```bash
python analyze_full_matrix_results.py
```

Or it runs automatically after the full matrix completes.

---

## Output Files

### Individual Scenario Results

Each scenario creates its own directory:
```
results/Phase2_DAILY/
├── 0_0_doh/
│   └── expansion_requirements_0_0_doh.csv
├── 3_0_doh/
│   └── expansion_requirements_3_0_doh.csv
├── 6_0_doh/
│   └── expansion_requirements_6_0_doh.csv
...
└── 21_14_doh/
    └── expansion_requirements_21_14_doh.csv
```

### Summary Analysis Files

The analysis script generates:

1. **`doh_full_matrix_summary.csv`**
   All 100 scenarios in rows with columns:
   - Domestic_DoH
   - International_DoH
   - Scenario
   - Sacramento_Shelves
   - Austin_Shelves
   - Total_Expansion

2. **`doh_matrix_TOTAL_EXPANSION.csv`**
   Pivot table (matrix view) of total expansion:
   - Rows: International DoH (0, 3, 6, 8, 10, 12, 15, 17, 19, 21)
   - Columns: Domestic DoH (0, 1, 2, 3, 4, 5, 7, 9, 11, 14)
   - Values: Total shelves required

3. **`doh_matrix_SACRAMENTO.csv`**
   Matrix view of Sacramento expansion only

4. **`doh_matrix_AUSTIN.csv`**
   Matrix view of Austin expansion only

### Example Matrix Output

```
TOTAL EXPANSION MATRIX (shelves)

Rows = International DoH, Columns = Domestic DoH

International_DoH   0      1      2      3      4      5      7      9     11     14
0                8,234  8,456  8,678  8,900  9,122  9,344  9,788 10,232 10,676 11,342
3                8,456  8,678  8,900  9,122  9,344  9,566 10,010 10,454 10,898 11,564
6                8,678  8,900  9,122  9,344  9,566  9,788 10,232 10,676 11,120 11,786
...
21              10,342 10,564 10,786 11,008 11,230 11,452 11,896 12,340 12,784 13,450
```

---

## Comparison: Main 10 vs. Full Matrix

### Main 10 Scenarios (run_all_scenarios.py)

The 10 **main scenarios** represent the diagonal plus strategic points:
- (0,0), (1,3), (2,6), (3,8), (4,10), (5,12), (7,15), (9,17), (11,19), (14,21)
- Runtime: ~30 minutes
- Use for: Quick sensitivity analysis

### Full Matrix (run_all_scenarios_FULL_MATRIX.py)

The **full matrix** covers all 100 combinations:
- All permutations of 10 domestic × 10 international values
- Runtime: ~5 hours
- Use for: Comprehensive analysis, creating heatmaps, finding optimal DoH combination

---

## Analysis Capabilities

With the full matrix results, you can:

1. **Identify optimal DoH balance**
   Find which (domestic, international) combination minimizes total expansion

2. **Analyze marginal impact**
   See how adding 1 day of DoH affects expansion requirements

3. **Create visualizations**
   Use pivot tables to create heatmaps showing expansion landscape

4. **Compare facility trade-offs**
   Understand how Sacramento vs. Austin expansion varies with DoH

5. **Sensitivity analysis**
   Determine which DoH dimension (domestic vs international) has greater impact

---

## Running Subsets of the Matrix

To run a custom subset, edit `run_all_scenarios_FULL_MATRIX.py`:

```python
# Example: Run only international DoH = 10
domestic_values = [0, 1, 2, 3, 4, 5, 7, 9, 11, 14]
international_values = [10]  # Only run international = 10

# Or run specific combinations
scenarios = [
    {"doh_intl": 10, "doh_dom": 3, "name": "10_3_doh"},
    {"doh_intl": 12, "doh_dom": 5, "name": "12_5_doh"},
    {"doh_intl": 15, "doh_dom": 7, "name": "15_7_doh"},
]
```

---

## Resuming After Interruption

If the full matrix run is interrupted, you can:

1. Check which scenarios completed:
```bash
ls results/Phase2_DAILY/
```

2. Edit `run_all_scenarios_FULL_MATRIX.py` to skip completed scenarios:
```python
completed_scenarios = ['0_0_doh', '3_0_doh', ...]  # List completed scenarios

for scenario in scenarios:
    if scenario['name'] in completed_scenarios:
        print(f"⏭️  Skipping {scenario['name']} (already completed)")
        continue
    # ... run scenario
```

3. Re-run the script to complete remaining scenarios

---

## Model Constraints (Applied to All 100 Scenarios)

All scenarios use identical constraints:

1. **93% capacity utilization**
   - Columbus: 93% of current capacity (cannot expand)
   - Sacramento/Austin: 100% current + 93% of expansion only

2. **Pallet expansion limits**
   - Sacramento: Max 2,810 pallet shelves
   - Austin: Max 2,250 pallet shelves

3. **Slack variables**
   - Penalty weights: demand (1000), doh (10), shelf (100), pallet_expansion (500)

4. **Daily time granularity**
   - 2,520 time periods (120 months × 21 business days)
   - Uniform demand distribution

5. **Set packing configurations**
   - Uses Phase 1 results for optimal package arrangements

---

## Performance Tips

**For faster execution:**

1. **Use parallel processing** (requires modification):
   - Run multiple scenarios simultaneously on different cores
   - Requires careful resource management

2. **Adjust solver time limit** (currently 180 seconds per scenario):
   ```python
   # In phase2_DAILY_parameterized.py
   parser.add_argument('--max_time', type=int, default=120)  # Reduce to 120 sec
   ```

3. **Run overnight or on high-performance machine**
   - Full matrix is computationally intensive

---

## Troubleshooting

**Issue: Scenario fails to converge**
- Check solver output for infeasibility messages
- Review slack variable values in results
- Verify Lead Time CSV was generated correctly

**Issue: Missing results**
- Check console output for error messages
- Verify scenario completed (check timestamp in results folder)
- Re-run failed scenarios individually for detailed diagnostics

**Issue: Analysis script reports missing scenarios**
- Not all scenarios may have completed
- Run analysis script anyway - it will report which scenarios are missing

---

## Files Overview

| File | Purpose | Runtime |
|------|---------|---------|
| `generate_lead_time_files_FULL_MATRIX.py` | Create 100 Lead Time CSVs | ~30 seconds |
| `run_all_scenarios_FULL_MATRIX.py` | Run all 100 optimizations | ~5 hours |
| `analyze_full_matrix_results.py` | Post-process and create matrices | ~5 seconds |
| `phase2_DAILY_parameterized.py` | Core optimization model | 2-4 min/scenario |

---

## Next Steps After Full Matrix Completes

1. **Review summary statistics**
   Check min/max/mean expansion requirements

2. **Examine pivot tables**
   Identify patterns in Sacramento vs Austin expansion

3. **Create visualizations** (external tool like Excel/Python)
   - Heatmaps of expansion requirements
   - Contour plots showing DoH trade-offs
   - 3D surface plots

4. **Select optimal DoH policy**
   Choose scenario that balances:
   - Total expansion cost
   - Service level requirements
   - Operational complexity

5. **Sensitivity analysis**
   Determine how robust optimal solution is to DoH variations
