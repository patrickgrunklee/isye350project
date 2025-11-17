# How to Run Full DoH Matrix (100 Scenarios)

## Quick Start - Two Options

### Option 1: Run Everything At Once (Recommended)

**Single command:**
```bash
python run_all_scenarios_FULL_MATRIX.py
```

This automatically:
1. Checks if Lead Time files exist (generates if needed)
2. Runs all 100 optimization scenarios
3. Shows progress for each scenario
4. Reports success/failure summary

**Time:** ~5 hours (300 minutes)

**Note:** The script will ask for confirmation before starting:
```
Run all 100 scenarios? (y/n):
```

---

### Option 2: Step-by-Step (For More Control)

**Step 1: Generate Lead Time files first**
```bash
python generate_lead_time_files_FULL_MATRIX.py
```
Output: Creates 100 CSV files in `Model Data/` folder
Time: ~30 seconds

**Step 2: Run all 100 scenarios**
```bash
python run_all_scenarios_FULL_MATRIX.py
```
Output: Creates 100 result folders in `results/Phase2_DAILY/`
Time: ~5 hours

**Step 3: Analyze results**
```bash
python analyze_full_matrix_results.py
```
Output: Creates summary CSVs and pivot tables
Time: ~5 seconds

---

## What You'll Get

### Individual Results
Each scenario gets its own folder:
```
results/Phase2_DAILY/
├── 0_0_doh/expansion_requirements_0_0_doh.csv
├── 3_0_doh/expansion_requirements_3_0_doh.csv
├── 6_0_doh/expansion_requirements_6_0_doh.csv
...
└── 21_14_doh/expansion_requirements_21_14_doh.csv
```

### Summary Files
Located in `results/Phase2_DAILY/`:

1. **doh_full_matrix_summary.csv**
   - All 100 scenarios in a table
   - Columns: Domestic_DoH, International_DoH, Sacramento_Shelves, Austin_Shelves, Total_Expansion

2. **doh_matrix_TOTAL_EXPANSION.csv**
   - 10×10 matrix showing total expansion for each (domestic, international) combination
   - Ready to visualize as heatmap

3. **doh_matrix_SACRAMENTO.csv**
   - Sacramento-only expansion matrix

4. **doh_matrix_AUSTIN.csv**
   - Austin-only expansion matrix

---

## Monitoring Progress

While running, you'll see:
```
================================================================================
SCENARIO 23/100: 8_2_doh
Progress: 22/100 completed (22.0%)
================================================================================

Running scenario with International DoH: 8, Domestic DoH: 2

[1/8] Setting up GAMSPy environment...
[2/8] Loading demand data (120 months)...
...
✓ Optimization complete!

✓ 8_2_doh completed successfully
```

---

## What Each Scenario Does

For each (domestic, international) DoH combination:

1. Loads correct Lead Time CSV
2. Runs optimization with:
   - 2,520 daily time periods
   - 93% capacity utilization constraint
   - Sacramento limit: 2,810 pallet shelves
   - Austin limit: 2,250 pallet shelves
   - Slack variables for constraint violations
3. Saves expansion requirements

---

## If Something Goes Wrong

**Scenario fails to solve:**
- Check the console output for error messages
- Review `results/Phase2_DAILY/{scenario_name}/` for partial results
- Script will continue with remaining scenarios

**Run was interrupted:**
- Check which scenarios completed: `ls results/Phase2_DAILY/`
- Manually remove incomplete scenario folders
- Re-run the script (it will regenerate missing scenarios)

**Out of memory:**
- Close other applications
- Run on a machine with more RAM (8GB+ recommended)
- Consider running main 10 scenarios first: `python run_all_scenarios.py`

---

## Comparison: Main 10 vs Full Matrix

| Feature | Main 10 Scenarios | Full Matrix |
|---------|-------------------|-------------|
| Command | `python run_all_scenarios.py` | `python run_all_scenarios_FULL_MATRIX.py` |
| Scenarios | 10 (diagonal + strategic points) | 100 (all combinations) |
| Runtime | ~30 minutes | ~5 hours |
| Use Case | Quick sensitivity check | Comprehensive analysis |
| Output | `doh_sensitivity_summary.csv` | `doh_full_matrix_summary.csv` + pivot tables |

**Recommendation:** Start with main 10 scenarios to verify everything works, then run full matrix overnight or during off-hours.

---

## After Full Matrix Completes

1. **Review summary statistics** (printed to console):
   - Minimum expansion scenario
   - Maximum expansion scenario
   - Mean/median expansion

2. **Open pivot tables** in Excel/spreadsheet:
   - `doh_matrix_TOTAL_EXPANSION.csv` - see expansion landscape
   - Identify optimal DoH combination

3. **Create visualizations**:
   - Import pivot tables into Excel
   - Create conditional formatting heatmap
   - Or use Python/R for 3D surface plots

4. **Select optimal DoH policy**:
   - Find scenario with minimum total expansion
   - Consider trade-offs (e.g., slightly more expansion but easier operations)

---

## Files Reference

| File | Purpose |
|------|---------|
| `run_all_scenarios_FULL_MATRIX.py` | Main script - runs all 100 scenarios |
| `generate_lead_time_files_FULL_MATRIX.py` | Creates 100 Lead Time CSV files |
| `analyze_full_matrix_results.py` | Post-processes results into pivot tables |
| `phase2_DAILY_parameterized.py` | Core optimization model (called 100 times) |
| `FULL_MATRIX_README.md` | Detailed documentation |

---

## Next Steps

**To start the full matrix run:**

```bash
cd "C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0"
python run_all_scenarios_FULL_MATRIX.py
```

Type `y` when prompted, then wait ~5 hours for completion.

**Pro tip:** Run overnight or during lunch break!
