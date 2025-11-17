"""
Analyze All Facilities Year 10 Daily Capacity Utilization by Storage Type

This script analyzes the capacity utilization for all facilities during year 10
(months 109-120) broken down by storage type (Racking, Pallet, Bins, Hazmat).

Assumes 10/3 DoH scenario with recommended expansion implemented:
- Columbus: 3,080 pallet shelves (no expansion - cannot expand)
- Sacramento: 2,670 pallet shelves (+1,570 expansion)
- Austin: 1,788 pallet shelves (+304 expansion)
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from pathlib import Path

# Directories
MODEL_DIR = Path(__file__).parent
DATA_DIR = MODEL_DIR / "Model Data"
RESULTS_DIR = MODEL_DIR / "results" / "Year10_Analysis"
PHASE1_DIR = MODEL_DIR / "results" / "Phase1_SetPacking"

# Ensure output directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*80)
print("All Facilities Year 10 Daily Capacity Utilization by Storage Type")
print("="*80)

# Load data
print("\n[1/5] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_pure_sku_discrete.csv')

print(f"   ✓ Loaded {len(demand_df)} months of demand data")
print(f"   ✓ Loaded {len(packing_configs_df)} packing configurations")

# Constants
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Pallet', 'Racking', 'Bins', 'Hazmat']
skus = [f'SKU{x}' for x in ['W1', 'W2', 'W3', 'A1', 'A2', 'A3', 'T1', 'T2', 'T3', 'T4',
                             'D1', 'D2', 'D3', 'C1', 'C2', 'E1', 'E2', 'E3']]

year10_months = list(range(109, 121))  # Months 109-120
days_per_month = 21
working_days_per_month = 21

# From 10/3 DoH DAILY model results - All facilities expansion
expansion_plan = {
    'Columbus': {'Pallet': 0, 'Bins': 0, 'Racking': 0, 'Hazmat': 0},
    'Sacramento': {'Pallet': 1570, 'Bins': 0, 'Racking': 0, 'Hazmat': 0},
    'Austin': {'Pallet': 304, 'Bins': 0, 'Racking': 0, 'Hazmat': 0}
}

print("\n[2/5] Calculating shelf capacity by storage type for all facilities...")

# Get current shelving for all facilities
shelf_capacity = {}  # (facility, storage_type) -> total_shelves
for _, row in shelving_count_df.iterrows():
    facility = str(row['Facility']).strip()
    st_raw = str(row['Shelving Type']).strip()
    # Normalize storage type name
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
    expansion_shelves = expansion_plan[facility].get(st, 0)
    total_shelves = current_shelves + expansion_shelves
    shelf_capacity[(facility, st)] = total_shelves

    if expansion_shelves > 0:
        print(f"   {facility} {st}: {current_shelves} + {expansion_shelves} = {total_shelves} shelves")
    else:
        print(f"   {facility} {st}: {total_shelves} shelves (no expansion)")

print("\n[3/5] Mapping SKUs to storage types and calculating capacity...")

# Map each SKU to its storage type
sku_to_storage_type = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    storage_method = str(row['Storage Method']).strip().lower()

    if 'bin' in storage_method:
        st = 'Bins'
    elif 'hazmat' in storage_method:
        st = 'Hazmat'
    elif 'rack' in storage_method:
        st = 'Racking'
    elif 'pallet' in storage_method:
        st = 'Pallet'
    else:
        st = 'Bins'  # Default

    sku_to_storage_type[sku] = st

# Calculate capacity per storage type (total units that can be stored)
# From packing configurations - get units per shelf for Austin
storage_type_capacity = {st: 0 for st in storage_types}

for _, config in packing_configs_df.iterrows():
    if config['Facility'] == 'Austin':
        st = config['Storage_Type']
        sku = config['SKU']

        # Calculate units per shelf for this configuration
        total_packages = config['Total_Packages_per_Shelf']
        units_per_package = config['Units_per_Package']
        units_per_shelf = total_packages * units_per_package

        # Track maximum capacity per storage type across all SKUs
        # (We'll calculate actual usage per SKU later)
        if sku in sku_to_storage_type:
            # Store units per shelf per SKU
            if not hasattr(storage_type_capacity, 'sku_capacity'):
                storage_type_capacity = {st: {} for st in storage_types}

            if st not in storage_type_capacity:
                storage_type_capacity[st] = {}

            storage_type_capacity[st][sku] = units_per_shelf

# Recalculate with proper structure - now include all facilities
sku_capacity_per_shelf = {}  # (facility, storage_type, sku) -> units_per_shelf

for _, config in packing_configs_df.iterrows():
    facility = config['Facility']
    st = config['Storage_Type']
    sku = config['SKU']

    total_packages = config['Total_Packages_per_Shelf']
    units_per_package = config['Units_per_Package']
    units_per_shelf = total_packages * units_per_package

    sku_capacity_per_shelf[(facility, st, sku)] = units_per_shelf

print("\n   SKU to Storage Type mapping (sample from Austin):")
for sku, st in sorted(sku_to_storage_type.items()):
    capacity = sku_capacity_per_shelf.get(('Austin', st, sku), 0)
    if capacity > 0:
        print(f"   {sku} → {st} ({capacity} units/shelf)")

print("\n[4/5] Calculating daily utilization for Year 10...")

# Calculate daily demand for year 10
daily_utilization_records = []

for month in year10_months:
    print(f"\n   Processing Month {month}...")

    # Get monthly demand for this month
    month_demand = {}
    for sku in skus:
        if sku in demand_df.columns:
            month_demand[sku] = demand_df.loc[month - 1, sku]  # 0-indexed
        else:
            month_demand[sku] = 0

    # Calculate daily demand (assume uniform distribution within month)
    daily_demand = {sku: month_demand[sku] / working_days_per_month for sku in skus}

    # For each day in the month
    for day in range(1, days_per_month + 1):
        # First, calculate total inventory needed across ALL facilities (this is single-counted)
        # Then calculate total capacity across ALL facilities
        # Then calculate per-facility breakdown

        # SYSTEM-WIDE utilization by storage type
        system_storage_utilization = {st: {'used': 0, 'capacity': 0} for st in storage_types}

        for st in storage_types:
            # Total inventory needed for all SKUs using this storage type (SINGLE COUNT)
            total_inventory_needed = 0

            for sku in skus:
                if sku_to_storage_type.get(sku) == st:
                    # Daily inventory needed (with 10/3 DoH)
                    doh = 6.5  # Average between international (10) and domestic (3)
                    sku_inventory_needed = daily_demand[sku] * doh
                    total_inventory_needed += sku_inventory_needed

            # Total capacity across ALL facilities for this storage type
            total_capacity_system = 0
            for facility in facilities:
                for sku in skus:
                    if sku_to_storage_type.get(sku) == st:
                        units_per_shelf = sku_capacity_per_shelf.get((facility, st, sku), 0)
                        num_shelves = shelf_capacity.get((facility, st), 0)
                        sku_capacity_at_facility = units_per_shelf * num_shelves
                        total_capacity_system += sku_capacity_at_facility

            system_storage_utilization[st]['used'] = total_inventory_needed
            system_storage_utilization[st]['capacity'] = total_capacity_system

        # Record system-wide utilization
        for st in storage_types:
            capacity = system_storage_utilization[st]['capacity']
            used = system_storage_utilization[st]['used']
            utilization_pct = (used / capacity * 100) if capacity > 0 else 0

            daily_utilization_records.append({
                'Month': month,
                'Day': day,
                'Facility': 'SYSTEM_TOTAL',
                'Storage_Type': st,
                'Total_Capacity_Units': capacity,
                'Used_Units': used,
                'Utilization_Pct': utilization_pct
            })

        # Now calculate per-facility breakdown (for reference)
        # This shows capacity at each facility, but demand is system-wide
        for facility in facilities:
            storage_utilization = {st: {'used': 0, 'capacity': 0} for st in storage_types}

            for st in storage_types:
                # Capacity at this facility for this storage type
                total_capacity = 0

                for sku in skus:
                    if sku_to_storage_type.get(sku) == st:
                        units_per_shelf = sku_capacity_per_shelf.get((facility, st, sku), 0)
                        num_shelves = shelf_capacity.get((facility, st), 0)
                        sku_total_capacity = units_per_shelf * num_shelves
                        total_capacity += sku_total_capacity

                storage_utilization[st]['capacity'] = total_capacity
                storage_utilization[st]['used'] = system_storage_utilization[st]['used']  # Same demand across all

            # Calculate utilization percentages (if this facility handled ALL demand)
            for st in storage_types:
                capacity = storage_utilization[st]['capacity']
                used = storage_utilization[st]['used']
                utilization_pct = (used / capacity * 100) if capacity > 0 else 0

                daily_utilization_records.append({
                    'Month': month,
                    'Day': day,
                    'Facility': facility,
                    'Storage_Type': st,
                    'Total_Capacity_Units': capacity,
                    'Used_Units': used,
                    'Utilization_Pct': utilization_pct
                })

print("\n[5/5] Generating output files...")

# Create DataFrame
utilization_df = pd.DataFrame(daily_utilization_records)

# Save detailed CSV
csv_path = RESULTS_DIR / "all_facilities_year10_storage_type_utilization.csv"
utilization_df.to_csv(csv_path, index=False)
print(f"\n   ✓ Saved detailed CSV: {csv_path}")

# Generate summary statistics
summary_path = RESULTS_DIR / "all_facilities_year10_storage_summary.txt"

with open(summary_path, 'w') as f:
    f.write("="*80 + "\n")
    f.write("All Facilities - Year 10 Storage Type Utilization Summary\n")
    f.write("="*80 + "\n")
    f.write(f"\nAnalysis Period: Months 109-120 (Year 10)\n")
    f.write(f"Days Analyzed: {len(year10_months) * days_per_month} business days\n")
    f.write(f"Scenario: 10/3 Days-on-Hand with Recommended Expansion\n")
    f.write(f"\nExpansion Applied:\n")
    f.write(f"  - Columbus: No expansion (cannot expand)\n")
    f.write(f"  - Sacramento: +1,570 Pallet shelves\n")
    f.write(f"  - Austin: +304 Pallet shelves\n")

    # SYSTEM-WIDE UTILIZATION (most important - this is the true utilization)
    f.write("\n" + "="*80 + "\n")
    f.write("SYSTEM-WIDE UTILIZATION (ACROSS ALL FACILITIES)\n")
    f.write("="*80 + "\n")
    f.write("\nThis shows true utilization: Total demand / Total capacity across all facilities\n")

    system_data = utilization_df[utilization_df['Facility'] == 'SYSTEM_TOTAL']

    for st in storage_types:
        st_data = system_data[system_data['Storage_Type'] == st]

        if len(st_data) > 0 and st_data['Total_Capacity_Units'].iloc[0] > 0:
            avg_util = st_data['Utilization_Pct'].mean()
            max_util = st_data['Utilization_Pct'].max()
            min_util = st_data['Utilization_Pct'].min()
            peak_row = st_data.loc[st_data['Utilization_Pct'].idxmax()]

            f.write(f"\n{st}:\n")
            f.write(f"  Average Utilization: {avg_util:.2f}%\n")
            f.write(f"  Peak Utilization: {max_util:.2f}% (Month {int(peak_row['Month'])}, Day {int(peak_row['Day'])})\n")
            f.write(f"  Minimum Utilization: {min_util:.2f}%\n")
            f.write(f"  Average Capacity Used: {st_data['Used_Units'].mean():,.0f} units\n")
            f.write(f"  Total System Capacity: {st_data['Total_Capacity_Units'].iloc[0]:,.0f} units\n")
            f.write(f"  Excess Capacity: {st_data['Total_Capacity_Units'].iloc[0] - st_data['Used_Units'].mean():,.0f} units\n")

    # For each facility
    for facility in facilities:
        f.write("\n" + "="*80 + "\n")
        f.write(f"{facility.upper()} FACILITY\n")
        f.write("="*80 + "\n")

        f.write("\nShelf Capacity by Storage Type:\n")
        for st in storage_types:
            num_shelves = shelf_capacity.get((facility, st), 0)
            if num_shelves > 0:
                f.write(f"  {st}: {num_shelves:,} shelves\n")

        f.write("\nUtilization Statistics by Storage Type:\n")
        for st in storage_types:
            st_data = utilization_df[(utilization_df['Storage_Type'] == st) &
                                      (utilization_df['Facility'] == facility)]

            if len(st_data) > 0 and st_data['Total_Capacity_Units'].iloc[0] > 0:
                avg_util = st_data['Utilization_Pct'].mean()
                max_util = st_data['Utilization_Pct'].max()
                min_util = st_data['Utilization_Pct'].min()

                # Find peak day
                peak_row = st_data.loc[st_data['Utilization_Pct'].idxmax()]

                f.write(f"\n  {st}:\n")
                f.write(f"    Average Utilization: {avg_util:.2f}%\n")
                f.write(f"    Peak Utilization: {max_util:.2f}% (Month {int(peak_row['Month'])}, Day {int(peak_row['Day'])})\n")
                f.write(f"    Minimum Utilization: {min_util:.2f}%\n")
                f.write(f"    Average Capacity Used: {st_data['Used_Units'].mean():,.0f} units\n")
                f.write(f"    Total Capacity Available: {st_data['Total_Capacity_Units'].iloc[0]:,.0f} units\n")

    f.write("\n" + "="*80 + "\n")
    f.write("FACILITY COMPARISON - AVERAGE UTILIZATION BY STORAGE TYPE\n")
    f.write("="*80 + "\n")

    for st in storage_types:
        f.write(f"\n{st}:\n")
        for facility in facilities:
            st_data = utilization_df[(utilization_df['Storage_Type'] == st) &
                                      (utilization_df['Facility'] == facility)]
            if len(st_data) > 0 and st_data['Total_Capacity_Units'].iloc[0] > 0:
                avg_util = st_data['Utilization_Pct'].mean()
                f.write(f"  {facility}: {avg_util:.2f}%\n")

print(f"   ✓ Saved summary: {summary_path}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print(f"\nOutput files:")
print(f"  1. {csv_path}")
print(f"  2. {summary_path}")
print("\n")
