"""
Year 10 Capacity Analysis for 10/3 DoH Model

This script analyzes the daily shelf capacity utilization for year 10 (months 109-120)
of the multiperiod model with 10/3 days-on-hand, assuming recommended expansion.

Output:
- year10_daily_capacity.csv: Daily capacity by SKU, facility, day
- year10_capacity_summary.txt: Summary statistics
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\Model Data")
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase1_SetPacking")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Year10_Analysis")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print("YEAR 10 CAPACITY ANALYSIS - 10/3 DoH Model")
print("="*100)

# Load demand data
print("\n[1/5] Loading demand and configuration data...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_pure_sku_discrete.csv')
print("   ✓ Data loaded")

# From the 10/3 DoH DAILY model results:
# Sacramento: Need 1,570 more pallet shelves (current: 1,100) = 2,670 total
# Austin: Need 304 more pallet shelves (current: 1,484) = 1,788 total
# Columbus: No expansion (3,080 pallet shelves)

expansion_plan = {
    'Columbus': {'Pallet': 0, 'Bins': 0, 'Racking': 0, 'Hazmat': 0},
    'Sacramento': {'Pallet': 1570, 'Bins': 0, 'Racking': 0, 'Hazmat': 0},
    'Austin': {'Pallet': 304, 'Bins': 0, 'Racking': 0, 'Hazmat': 0}
}

print("\n[2/5] Calculating post-expansion shelf capacity...")
# Get current shelves and add expansion
shelf_capacity = {}
for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st_raw = row['Shelving Type'].strip()

    if 'Pallet' in st_raw:
        st = 'Pallet'
    elif 'Bin' in st_raw:
        st = 'Bins'
    elif 'Rack' in st_raw:
        st = 'Racking'
    elif 'Hazmat' in st_raw:
        st = 'Hazmat'
    else:
        st = st_raw

    current_shelves = int(row['Number of Shelves'])
    expansion = expansion_plan.get(fac, {}).get(st, 0)
    total_shelves = current_shelves + expansion

    shelf_capacity[(fac, st)] = total_shelves

print("   Post-expansion shelf capacity:")
for (fac, st), shelves in shelf_capacity.items():
    if st == 'Pallet':
        current = int(shelving_count_df[(shelving_count_df['Facility'].str.strip() == fac) &
                                        (shelving_count_df['Shelving Type'].str.contains('Pallet'))]['Number of Shelves'].values[0])
        print(f"   {fac:12} {st:10}: {current:5} → {shelves:5} shelves (+{shelves-current})")

# Extract year 10 demand (months 109-120)
print("\n[3/5] Extracting year 10 demand (months 109-120)...")
year10_months = list(range(109, 121))
skus = [col for col in demand_df.columns if col.startswith('SKU')]
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
days_per_month = 21

# Calculate daily demand for year 10
year10_daily_demand = []
for month_idx, month in enumerate(year10_months, start=109):
    monthly_demand = demand_df.iloc[month - 1]  # 0-indexed

    for day in range(1, days_per_month + 1):
        for sku in skus:
            # Distribute monthly demand evenly across 21 days
            daily_demand_value = monthly_demand[sku] / days_per_month

            year10_daily_demand.append({
                'Month': month,
                'Day': day,
                'Date_String': f"M{month}D{day}",
                'SKU': sku,
                'Daily_Demand': daily_demand_value
            })

year10_demand_df = pd.DataFrame(year10_daily_demand)
print(f"   ✓ Extracted {len(year10_demand_df)} daily demand records for year 10")

# Calculate capacity per SKU per facility based on configurations
print("\n[4/5] Calculating shelf capacity by SKU and facility...")

# Group configurations by SKU and facility
sku_facility_capacity = {}
for _, config in packing_configs_df.iterrows():
    sku = config['SKU']
    fac = config['Facility']
    st = config['Storage_Type']
    units_per_shelf = config['Total_Packages_per_Shelf'] * config['Units_per_Package']

    key = (sku, fac, st)
    if key not in sku_facility_capacity:
        sku_facility_capacity[key] = units_per_shelf
    else:
        # Take maximum capacity configuration
        sku_facility_capacity[key] = max(sku_facility_capacity[key], units_per_shelf)

# Calculate total capacity per SKU per facility (across all storage types)
total_capacity_by_sku_facility = {}
for (sku, fac, st), units_per_shelf in sku_facility_capacity.items():
    total_shelves = shelf_capacity.get((fac, st), 0)
    total_capacity = units_per_shelf * total_shelves

    if (sku, fac) not in total_capacity_by_sku_facility:
        total_capacity_by_sku_facility[(sku, fac)] = 0
    total_capacity_by_sku_facility[(sku, fac)] += total_capacity

print(f"   ✓ Calculated capacity for {len(total_capacity_by_sku_facility)} SKU-Facility combinations")

# Create daily capacity records for year 10
print("\n[5/5] Generating year 10 daily capacity analysis...")
capacity_records = []

for month in year10_months:
    for day in range(1, days_per_month + 1):
        for sku in skus:
            # Get daily demand for this SKU on this day
            demand_row = year10_demand_df[
                (year10_demand_df['Month'] == month) &
                (year10_demand_df['Day'] == day) &
                (year10_demand_df['SKU'] == sku)
            ]
            daily_demand = demand_row['Daily_Demand'].values[0] if len(demand_row) > 0 else 0

            for fac in facilities:
                # Get capacity for this SKU at this facility
                capacity = total_capacity_by_sku_facility.get((sku, fac), 0)

                # Calculate utilization
                utilization_pct = (daily_demand / capacity * 100) if capacity > 0 else 0

                capacity_records.append({
                    'Month': month,
                    'Day': day,
                    'Date_String': f"M{month}D{day}",
                    'Year': 10,
                    'SKU': sku,
                    'Facility': fac,
                    'Daily_Demand': daily_demand,
                    'Facility_Capacity': capacity,
                    'Utilization_Pct': utilization_pct,
                    'Available_Capacity': capacity - daily_demand
                })

capacity_df = pd.DataFrame(capacity_records)

# Save detailed CSV
output_csv = RESULTS_DIR / 'year10_daily_capacity.csv'
capacity_df.to_csv(output_csv, index=False)
print(f"   ✓ Saved detailed capacity analysis to {output_csv}")

# Generate summary report
print("\n" + "="*100)
print("GENERATING SUMMARY REPORT")
print("="*100)

summary_lines = []
summary_lines.append("="*100)
summary_lines.append("YEAR 10 CAPACITY ANALYSIS SUMMARY - 10/3 DoH Model")
summary_lines.append("="*100)
summary_lines.append("")
summary_lines.append("Analysis Period: Year 10 (Months 109-120)")
summary_lines.append("Time Granularity: Daily (21 business days per month)")
summary_lines.append("Total Days Analyzed: 252 days (12 months × 21 days)")
summary_lines.append("")

summary_lines.append("="*100)
summary_lines.append("POST-EXPANSION SHELF CAPACITY")
summary_lines.append("="*100)
summary_lines.append("")
for (fac, st), total_shelves in shelf_capacity.items():
    if st == 'Pallet':
        current = int(shelving_count_df[(shelving_count_df['Facility'].str.strip() == fac) &
                                        (shelving_count_df['Shelving Type'].str.contains('Pallet'))]['Number of Shelves'].values[0])
        expansion = total_shelves - current
        summary_lines.append(f"{fac:12} {st:10}: {current:5} + {expansion:5} = {total_shelves:5} shelves")

summary_lines.append("")
summary_lines.append("="*100)
summary_lines.append("AVERAGE UTILIZATION BY FACILITY (Year 10)")
summary_lines.append("="*100)
summary_lines.append("")

for fac in facilities:
    fac_data = capacity_df[capacity_df['Facility'] == fac]
    avg_util = fac_data['Utilization_Pct'].mean()
    max_util = fac_data['Utilization_Pct'].max()
    min_util = fac_data['Utilization_Pct'].min()

    summary_lines.append(f"{fac:12}: Avg: {avg_util:6.2f}%  |  Max: {max_util:6.2f}%  |  Min: {min_util:6.2f}%")

summary_lines.append("")
summary_lines.append("="*100)
summary_lines.append("TOP 10 HIGHEST UTILIZATION DAYS (Facility-SKU)")
summary_lines.append("="*100)
summary_lines.append("")

top_util = capacity_df.nlargest(10, 'Utilization_Pct')[
    ['Date_String', 'Facility', 'SKU', 'Daily_Demand', 'Facility_Capacity', 'Utilization_Pct']
]
summary_lines.append(top_util.to_string(index=False))

summary_lines.append("")
summary_lines.append("="*100)
summary_lines.append("SKU-LEVEL STATISTICS (Aggregated across all facilities)")
summary_lines.append("="*100)
summary_lines.append("")

sku_stats = capacity_df.groupby('SKU').agg({
    'Daily_Demand': 'mean',
    'Facility_Capacity': 'mean',
    'Utilization_Pct': 'mean'
}).round(2)
sku_stats = sku_stats.sort_values('Utilization_Pct', ascending=False)
summary_lines.append(sku_stats.to_string())

summary_lines.append("")
summary_lines.append("="*100)
summary_lines.append("MONTHLY TRENDS (Year 10)")
summary_lines.append("="*100)
summary_lines.append("")

monthly_stats = capacity_df.groupby('Month').agg({
    'Daily_Demand': 'sum',
    'Utilization_Pct': 'mean'
}).round(2)
monthly_stats.columns = ['Total_Daily_Demand', 'Avg_Utilization_Pct']
summary_lines.append(monthly_stats.to_string())

summary_lines.append("")
summary_lines.append("="*100)
summary_lines.append("END OF SUMMARY")
summary_lines.append("="*100)

# Save summary
summary_file = RESULTS_DIR / 'year10_capacity_summary.txt'
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(summary_lines))

print(f"   ✓ Saved summary report to {summary_file}")

# Print summary to console
print("\n" + '\n'.join(summary_lines))

print("\n" + "="*100)
print("YEAR 10 CAPACITY ANALYSIS COMPLETE")
print("="*100)
print(f"\nOutput files:")
print(f"  1. Detailed CSV: {output_csv}")
print(f"  2. Summary TXT:  {summary_file}")
print("")
