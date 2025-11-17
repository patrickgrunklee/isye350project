"""
POST-RUN TRUCK UTILIZATION ANALYSIS
====================================

Apply truck dispatch analysis to any phase2_DAILY model results.

Usage:
    python analyze_truck_utilization.py <doh_config>

Examples:
    python analyze_truck_utilization.py 3_1_doh
    python analyze_truck_utilization.py 5_2_doh
    python analyze_truck_utilization.py 0_0_doh

This script:
1. Loads delivery results from any DoH model
2. Calculates truck requirements per supplier per day
3. Reports utilization percentages (weight and volume)
4. Identifies low-utilization deliveries (<90%)
5. Estimates potential truck savings from consolidation
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    SKU_TO_SUPPLIER,
    SUPPLIERS,
    calculate_truckloads,
    calculate_truck_utilization
)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
if len(sys.argv) > 1:
    DOH_CONFIG = sys.argv[1]
else:
    print("Usage: python analyze_truck_utilization.py <doh_config>")
    print("Example: python analyze_truck_utilization.py 3_1_doh")
    sys.exit(1)

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")

print("="*80)
print(f"TRUCK UTILIZATION ANALYSIS - {DOH_CONFIG.upper()}")
print("="*80)

# Check if truckload analysis already exists
truckload_file = RESULTS_DIR / f"truckload_analysis_{DOH_CONFIG}.csv"

if not truckload_file.exists():
    print(f"\nERROR: Truckload analysis file not found: {truckload_file}")
    print("Please run the corresponding phase2_DAILY model first.")
    sys.exit(1)

# Load existing truckload analysis
print(f"\nLoading: {truckload_file.name}")
truckload_df = pd.read_csv(truckload_file)

print(f"Total delivery events: {len(truckload_df):,}")

# Summary statistics
print("\n" + "="*80)
print("OVERALL TRUCK UTILIZATION")
print("="*80)

total_trucks = truckload_df['Trucks_Needed'].sum()
print(f"\nTotal trucks needed: {total_trucks:,.2f}")
print(f"Average trucks per delivery: {truckload_df['Trucks_Needed'].mean():.2f}")
print(f"Max trucks in single delivery: {truckload_df['Trucks_Needed'].max():.2f}")

print(f"\nAverage weight utilization: {truckload_df['Weight_Utilization_Pct'].mean():.1f}%")
print(f"Average volume utilization: {truckload_df['Volume_Utilization_Pct'].mean():.1f}%")

# Binding constraints
weight_binding = (truckload_df['Binding_Constraint'] == 'weight').sum()
volume_binding = (truckload_df['Binding_Constraint'] == 'volume').sum()
print(f"\nWeight-constrained: {weight_binding:,} ({weight_binding/len(truckload_df)*100:.1f}%)")
print(f"Volume-constrained: {volume_binding:,} ({volume_binding/len(truckload_df)*100:.1f}%)")

# Low utilization analysis
print("\n" + "="*80)
print("LOW UTILIZATION ANALYSIS (<90%)")
print("="*80)

# Deliveries below 90% on binding constraint
low_util = truckload_df[
    ((truckload_df['Binding_Constraint'] == 'weight') & (truckload_df['Weight_Utilization_Pct'] < 90)) |
    ((truckload_df['Binding_Constraint'] == 'volume') & (truckload_df['Volume_Utilization_Pct'] < 90))
]

print(f"\nDeliveries below 90% on binding constraint: {len(low_util):,} ({len(low_util)/len(truckload_df)*100:.1f}%)")

if len(low_util) > 0:
    print(f"Trucks in low-utilization deliveries: {low_util['Trucks_Needed'].sum():.2f}")

    # Estimate potential savings
    # If we could consolidate to 90%, how many trucks would we save?
    wasted_capacity = []
    for _, row in low_util.iterrows():
        if row['Binding_Constraint'] == 'weight':
            current_util = row['Weight_Utilization_Pct'] / 100
            if current_util < 0.90:
                # Could reduce trucks by (90% - current%) / 90%
                potential_reduction = row['Trucks_Needed'] * (0.90 - current_util) / 0.90
                wasted_capacity.append(potential_reduction)
        else:  # volume
            current_util = row['Volume_Utilization_Pct'] / 100
            if current_util < 0.90:
                potential_reduction = row['Trucks_Needed'] * (0.90 - current_util) / 0.90
                wasted_capacity.append(potential_reduction)

    potential_savings = sum(wasted_capacity)
    print(f"Potential truck savings if consolidated to 90%: {potential_savings:,.0f} trucks")
    print(f"Savings as % of total: {potential_savings/total_trucks*100:.1f}%")

    # Show worst offenders
    print("\nTop 10 worst utilization:")
    low_util_sorted = low_util.copy()
    low_util_sorted['Binding_Util'] = low_util_sorted.apply(
        lambda x: x['Weight_Utilization_Pct'] if x['Binding_Constraint'] == 'weight' else x['Volume_Utilization_Pct'],
        axis=1
    )
    low_util_sorted = low_util_sorted.sort_values('Binding_Util')

    for idx, (_, row) in enumerate(low_util_sorted.head(10).iterrows(), 1):
        binding_util = row['Weight_Utilization_Pct'] if row['Binding_Constraint'] == 'weight' else row['Volume_Utilization_Pct']
        print(f"  {idx}. {row['Supplier']} to {row['Facility']} (Month {row['Month']}, Day {row['Day']})")
        print(f"      {row['Trucks_Needed']:.2f} trucks at {binding_util:.1f}% {row['Binding_Constraint']} utilization")
else:
    print("\nExcellent! All deliveries meet 90% utilization threshold.")

# By supplier
print("\n" + "="*80)
print("BY SUPPLIER")
print("="*80)

for supplier in SUPPLIERS:
    supplier_data = truckload_df[truckload_df['Supplier'] == supplier]
    if len(supplier_data) > 0:
        print(f"\n{supplier}:")
        print(f"  Deliveries: {len(supplier_data):,}")
        print(f"  Total trucks: {supplier_data['Trucks_Needed'].sum():,.2f}")
        print(f"  Avg trucks/delivery: {supplier_data['Trucks_Needed'].mean():.2f}")
        print(f"  Avg weight utilization: {supplier_data['Weight_Utilization_Pct'].mean():.1f}%")
        print(f"  Avg volume utilization: {supplier_data['Volume_Utilization_Pct'].mean():.1f}%")

        low_util_supplier = supplier_data[
            ((supplier_data['Binding_Constraint'] == 'weight') & (supplier_data['Weight_Utilization_Pct'] < 90)) |
            ((supplier_data['Binding_Constraint'] == 'volume') & (supplier_data['Volume_Utilization_Pct'] < 90))
        ]
        if len(low_util_supplier) > 0:
            print(f"  Low utilization (<90%): {len(low_util_supplier):,} deliveries ({len(low_util_supplier)/len(supplier_data)*100:.1f}%)")

# By facility
print("\n" + "="*80)
print("BY FACILITY")
print("="*80)

for facility in ['Columbus', 'Sacramento', 'Austin']:
    facility_data = truckload_df[truckload_df['Facility'] == facility]
    if len(facility_data) > 0:
        print(f"\n{facility}:")
        print(f"  Deliveries: {len(facility_data):,}")
        print(f"  Total trucks: {facility_data['Trucks_Needed'].sum():,.2f}")
        print(f"  Avg trucks/delivery: {facility_data['Trucks_Needed'].mean():.2f}")
        print(f"  Avg weight utilization: {facility_data['Weight_Utilization_Pct'].mean():.1f}%")
        print(f"  Avg volume utilization: {facility_data['Volume_Utilization_Pct'].mean():.1f}%")

# Recommendations
print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

if volume_binding > weight_binding:
    print("\n1. VOLUME-CONSTRAINED OPERATIONS")
    print("   - Trucks fill by space before weight")
    print("   - Consider denser products or better packing")
    print(f"   - Unused weight capacity: ~{(1 - truckload_df['Weight_Utilization_Pct'].mean()/100)*TRUCK_WEIGHT_CAPACITY_LBS:,.0f} lbs per truck")
else:
    print("\n1. WEIGHT-CONSTRAINED OPERATIONS")
    print("   - Trucks max out on weight before volume")
    print("   - Consider lighter/bulkier products")
    print(f"   - Unused volume capacity: ~{(1 - truckload_df['Volume_Utilization_Pct'].mean()/100)*TRUCK_VOLUME_CAPACITY_CUFT:,.0f} cu ft per truck")

if len(low_util) > 0:
    print(f"\n2. CONSOLIDATION OPPORTUNITY")
    print(f"   - {len(low_util):,} deliveries below 90% utilization")
    print(f"   - Potential savings: {potential_savings:,.0f} trucks ({potential_savings/total_trucks*100:.1f}%)")
    print("   - Consider:")
    print("     * Adjusting delivery schedules to consolidate loads")
    print("     * Combining SKUs from same supplier")
    print("     * Delivering early to fill trucks")
else:
    print("\n2. EXCELLENT UTILIZATION")
    print("   - All deliveries meet 90% threshold")
    print("   - Truck dispatch is already optimized")

avg_skus = truckload_df['Num_SKUs'].mean()
print(f"\n3. SKU CONSOLIDATION")
print(f"   - Average {avg_skus:.2f} SKUs per delivery")
if avg_skus < 2:
    print("   - Consider bundling more SKUs from same supplier")
else:
    print("   - Good consolidation already achieved")

print("\n" + "="*80)
print(f"ANALYSIS COMPLETE - {DOH_CONFIG.upper()}")
print("="*80)
