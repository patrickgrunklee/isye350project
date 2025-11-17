"""
Analyze results from FULL MATRIX run and create visualization

Generates:
1. Summary CSV with all 100 scenarios
2. Pivot table (matrix view) of total expansion
3. Pivot tables for Sacramento and Austin separately
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")

# Define the values
domestic_values = [0, 1, 2, 3, 4, 5, 7, 9, 11, 14]
international_values = [0, 3, 6, 8, 10, 12, 15, 17, 19, 21]

print("="*80)
print("ANALYZING FULL MATRIX RESULTS")
print("="*80)
print()

# Collect all results
summary_data = []
missing_scenarios = []

for doh_intl in international_values:
    for doh_dom in domestic_values:
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
            missing_scenarios.append(scenario_name)

if missing_scenarios:
    print(f"⚠️  Warning: {len(missing_scenarios)} scenarios missing results:")
    for s in missing_scenarios[:10]:
        print(f"  - {s}")
    if len(missing_scenarios) > 10:
        print(f"  ... and {len(missing_scenarios) - 10} more")
    print()

if not summary_data:
    print("ERROR: No results found!")
    sys.exit(1)

# Create summary dataframe
summary_df = pd.DataFrame(summary_data)

# Save full summary
output_file = RESULTS_DIR / "doh_full_matrix_summary.csv"
summary_df.to_csv(output_file, index=False)
print(f"✓ Summary saved to: {output_file}")

# Create pivot tables (matrix views)
print("\nGenerating pivot tables...")

# Total expansion matrix
total_pivot = summary_df.pivot(
    index='International_DoH',
    columns='Domestic_DoH',
    values='Total_Expansion'
)
total_pivot_file = RESULTS_DIR / "doh_matrix_TOTAL_EXPANSION.csv"
total_pivot.to_csv(total_pivot_file)
print(f"✓ Total expansion matrix: {total_pivot_file}")

# Sacramento expansion matrix
sac_pivot = summary_df.pivot(
    index='International_DoH',
    columns='Domestic_DoH',
    values='Sacramento_Shelves'
)
sac_pivot_file = RESULTS_DIR / "doh_matrix_SACRAMENTO.csv"
sac_pivot.to_csv(sac_pivot_file)
print(f"✓ Sacramento matrix: {sac_pivot_file}")

# Austin expansion matrix
austin_pivot = summary_df.pivot(
    index='International_DoH',
    columns='Domestic_DoH',
    values='Austin_Shelves'
)
austin_pivot_file = RESULTS_DIR / "doh_matrix_AUSTIN.csv"
austin_pivot.to_csv(austin_pivot_file)
print(f"✓ Austin matrix: {austin_pivot_file}")

# Print statistics
print("\n" + "="*80)
print("FULL MATRIX STATISTICS")
print("="*80)
print(f"\nScenarios analyzed: {len(summary_data)}")
print(f"Missing scenarios: {len(missing_scenarios)}")
print()

print("Total Expansion Statistics:")
print(f"  Min:    {summary_df['Total_Expansion'].min():,.0f} shelves")
print(f"  Max:    {summary_df['Total_Expansion'].max():,.0f} shelves")
print(f"  Mean:   {summary_df['Total_Expansion'].mean():,.0f} shelves")
print(f"  Median: {summary_df['Total_Expansion'].median():,.0f} shelves")

print("\nScenario with minimum expansion:")
min_row = summary_df.loc[summary_df['Total_Expansion'].idxmin()]
print(f"  {min_row['Scenario']}: {min_row['Total_Expansion']:.0f} shelves")
print(f"  (Domestic: {min_row['Domestic_DoH']}, International: {min_row['International_DoH']})")

print("\nScenario with maximum expansion:")
max_row = summary_df.loc[summary_df['Total_Expansion'].idxmax()]
print(f"  {max_row['Scenario']}: {max_row['Total_Expansion']:.0f} shelves")
print(f"  (Domestic: {max_row['Domestic_DoH']}, International: {max_row['International_DoH']})")

print("\n" + "="*80)
print("TOTAL EXPANSION MATRIX (shelves)")
print("="*80)
print("\nRows = International DoH, Columns = Domestic DoH")
print()
print(total_pivot.to_string(float_format=lambda x: f'{x:,.0f}'))

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
