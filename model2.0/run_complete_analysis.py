"""
Master script to run complete DoH sensitivity analysis

This script:
1. Generates all required Lead Time CSV files
2. Runs all 10 DoH scenarios
3. Generates comparison report

Usage:
    python run_complete_analysis.py
"""
import subprocess
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("COMPLETE DOH SENSITIVITY ANALYSIS")
print("="*80)
print("\nThis will run all 10 DoH scenarios:")
print("  (0,0), (1,3), (2,6), (3,8), (4,10), (5,12), (7,15), (9,17), (11,19), (14,21)")
print()

# Step 1: Generate Lead Time files
print("\n" + "="*80)
print("STEP 1: GENERATING LEAD TIME FILES")
print("="*80)
try:
    result = subprocess.run(["python", "generate_lead_time_files.py"], check=True)
    print("\n✓ Lead time files generated successfully")
except subprocess.CalledProcessError as e:
    print(f"\n✗ Failed to generate lead time files (error code {e.returncode})")
    print("Fix the error and try again")
    sys.exit(1)

# Step 2: Run all scenarios
print("\n" + "="*80)
print("STEP 2: RUNNING ALL SCENARIOS")
print("="*80)
try:
    result = subprocess.run(["python", "run_all_scenarios.py"], check=True)
    print("\n✓ All scenarios completed")
except subprocess.CalledProcessError as e:
    print(f"\n✗ Some scenarios failed (error code {e.returncode})")
    print("Check the output above for details")
    sys.exit(1)

# Step 3: Generate comparison report
print("\n" + "="*80)
print("STEP 3: GENERATING COMPARISON REPORT")
print("="*80)

RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")

scenarios = [
    (0, 0), (1, 3), (2, 6), (3, 8), (4, 10),
    (5, 12), (7, 15), (9, 17), (11, 19), (14, 21)
]

import pandas as pd

summary_data = []
for doh_dom, doh_intl in scenarios:
    scenario_name = f"{doh_intl}_{doh_dom}_doh"
    result_file = RESULTS_DIR / scenario_name / f"expansion_requirements_{scenario_name}.csv"

    if result_file.exists():
        df = pd.read_csv(result_file)
        total_expansion = df[df['Facility'] == 'Total']['Expansion_Shelves'].values[0]
        sac_expansion = df[df['Facility'] == 'Sacramento']['Expansion_Shelves'].values[0]
        austin_expansion = df[df['Facility'] == 'Austin']['Expansion_Shelves'].values[0]

        summary_data.append({
            'Domestic_DoH': doh_dom,
            'International_DoH': doh_intl,
            'Scenario': scenario_name,
            'Sacramento_Shelves': sac_expansion,
            'Austin_Shelves': austin_expansion,
            'Total_Expansion': total_expansion
        })
    else:
        print(f"⚠️  Warning: Results not found for {scenario_name}")

if summary_data:
    summary_df = pd.DataFrame(summary_data)
    output_file = RESULTS_DIR / "doh_sensitivity_summary.csv"
    summary_df.to_csv(output_file, index=False)

    print("\n" + "="*80)
    print("DOH SENSITIVITY ANALYSIS SUMMARY")
    print("="*80)
    print(summary_df.to_string(index=False))

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_file}")
    print(f"\nIndividual scenario results in: {RESULTS_DIR}")
else:
    print("\n⚠️  No results found - scenarios may have failed")
    sys.exit(1)
