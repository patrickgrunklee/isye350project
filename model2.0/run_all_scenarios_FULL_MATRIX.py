"""
Run FULL MATRIX of all DoH combinations (100 scenarios)

This generates all combinations of:
- Domestic DoH: 0, 1, 2, 3, 4, 5, 7, 9, 11, 14
- International DoH: 0, 3, 6, 8, 10, 12, 15, 17, 19, 21

Total: 10 × 10 = 100 scenarios
"""
import subprocess
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Define the values for each dimension
domestic_values = [0, 1, 2, 3, 4, 5, 7, 9, 11, 14]
international_values = [0, 3, 6, 8, 10, 12, 15, 17, 19, 21]

# Generate all combinations (full matrix)
scenarios = []
for doh_intl in international_values:
    for doh_dom in domestic_values:
        scenarios.append({
            "doh_intl": doh_intl,
            "doh_dom": doh_dom,
            "name": f"{doh_intl}_{doh_dom}_doh"
        })

print("="*80)
print("RUNNING FULL MATRIX OF DOH SCENARIOS")
print("="*80)
print(f"\nTotal scenarios: {len(scenarios)}")
print(f"Domestic values: {domestic_values}")
print(f"International values: {international_values}")
print(f"\nEstimated time: ~{len(scenarios) * 3} minutes (~5 hours)")
print()

# Check if Lead Time files exist, generate if needed
print("Checking for Lead Time files...")
DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
missing_files = []
for scenario in scenarios:
    lead_time_file = DATA_DIR / f"Lead TIme_{scenario['doh_intl']}_{scenario['doh_dom']}_business_days.csv"
    if not lead_time_file.exists():
        missing_files.append(lead_time_file.name)

if missing_files:
    print(f"\n⚠️  {len(missing_files)} Lead Time files are missing")
    print("Generating Lead Time files now...")
    try:
        result = subprocess.run(["python", "generate_lead_time_files_FULL_MATRIX.py"], check=True)
        print("✓ Lead Time files generated successfully\n")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to generate Lead Time files (error code {e.returncode})")
        print("Please run 'python generate_lead_time_files_FULL_MATRIX.py' manually")
        sys.exit(1)
else:
    print(f"✓ All {len(scenarios)} Lead Time files found\n")

# Ask for confirmation
response = input("Run all 100 scenarios? (y/n): ")
if response.lower() != 'y':
    print("Cancelled by user")
    sys.exit(0)

failed_scenarios = []
completed = 0

for i, scenario in enumerate(scenarios, 1):
    print("\n" + "="*80)
    print(f"SCENARIO {i}/{len(scenarios)}: {scenario['name']}")
    print(f"Progress: {i-1}/{len(scenarios)} completed ({(i-1)/len(scenarios)*100:.1f}%)")
    print("="*80)

    cmd = [
        "python",
        "phase2_DAILY_parameterized.py",
        "--doh_intl", str(scenario['doh_intl']),
        "--doh_dom", str(scenario['doh_dom']),
        "--scenario_name", scenario['name']
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✓ {scenario['name']} completed successfully")
        completed += 1
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {scenario['name']} FAILED with error code {e.returncode}")
        failed_scenarios.append(scenario['name'])
    except Exception as e:
        print(f"\n✗ {scenario['name']} FAILED: {e}")
        failed_scenarios.append(scenario['name'])

print("\n" + "="*80)
print("BATCH RUN COMPLETE")
print("="*80)
print(f"\nCompleted: {completed}/{len(scenarios)} ({completed/len(scenarios)*100:.1f}%)")
if failed_scenarios:
    print(f"Failed: {len(failed_scenarios)} scenarios")
    print(f"Failed scenarios: {', '.join(failed_scenarios[:10])}")
    if len(failed_scenarios) > 10:
        print(f"  ... and {len(failed_scenarios) - 10} more")
else:
    print("✓ All 100 scenarios completed successfully!")

# Run analysis script automatically if most scenarios completed
if completed >= len(scenarios) * 0.8:  # At least 80% completed
    print("\n" + "="*80)
    print("RUNNING ANALYSIS")
    print("="*80)
    print("\nGenerating pivot tables and summary matrices...")
    try:
        result = subprocess.run(["python", "analyze_full_matrix_results.py"], check=True)
        print("\n✓ Analysis complete!")
        print(f"\nResults saved in: results/Phase2_DAILY/")
        print("  - doh_full_matrix_summary.csv")
        print("  - doh_matrix_TOTAL_EXPANSION.csv")
        print("  - doh_matrix_SACRAMENTO.csv")
        print("  - doh_matrix_AUSTIN.csv")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Analysis script failed (error code {e.returncode})")
        print("You can run it manually: python analyze_full_matrix_results.py")
else:
    print("\n⚠️  Too many scenarios failed - skipping automatic analysis")
    print("Fix errors and re-run failed scenarios, then run: python analyze_full_matrix_results.py")
