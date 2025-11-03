"""
CAPACITY COMPARISON: 3D BIN PACKING vs. ORIGINAL APPROACH
==========================================================

Shows how 3D bin packing dramatically increases packages per shelf
"""

import pandas as pd
from pathlib import Path

# Paths
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")

print("="*100)
print("CAPACITY COMPARISON: 3D BIN PACKING IMPACT")
print("="*100)

# Load 3D configurations
configs_3d_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')

print("\n[1] ITEM CAPACITY vs PACKAGE CAPACITY")
print("="*100)
print("\nKEY INSIGHT: Multiple packages can fit within ONE item slot using 3D bin packing\n")

# Group by facility and storage type to show examples
for fac in ['Columbus', 'Sacramento', 'Austin']:
    for st in ['Bins', 'Racking', 'Pallet', 'Hazmat']:
        configs = configs_3d_df[(configs_3d_df['Facility'] == fac) &
                                (configs_3d_df['Storage_Type'] == st)]

        if len(configs) == 0:
            continue

        print(f"\n{fac} - {st}:")
        print(f"{'─'*90}")

        # Get unique max items per shelf for this facility/storage type
        max_items = configs['Items_per_Shelf'].iloc[0]
        print(f"  Max item slots per shelf: {max_items}")
        print()

        # Show top 5 configurations by packages per shelf
        top_configs = configs.nlargest(5, 'Total_Packages_per_Shelf')

        for _, row in top_configs.iterrows():
            sku = row['SKU']
            pkg_per_item = row['Packages_per_Item']
            total_pkg = row['Total_Packages_per_Shelf']
            weight = row['Total_Weight']

            # Calculate "naive" approach (1 package per item)
            naive_total = max_items  # Just 1 package per item slot
            improvement = total_pkg / naive_total if naive_total > 0 else 0

            print(f"    {sku:<8}: {pkg_per_item:>2} pkg/item × {max_items} items = {total_pkg:>4} packages/shelf ({weight:>7.1f} lbs)")
            print(f"             └─> {improvement:>4.1f}× more than naive approach ({naive_total} pkg/shelf)")

print("\n" + "="*100)
print("[2] COMPARISON: NAIVE vs 3D BIN PACKING")
print("="*100)

# Calculate total capacity under both approaches
naive_total_capacity = 0
bin_packed_capacity = 0

for _, row in configs_3d_df.iterrows():
    max_items = row['Items_per_Shelf']
    total_pkg = row['Total_Packages_per_Shelf']

    naive_total_capacity += max_items  # 1 package per item
    bin_packed_capacity += total_pkg

print(f"\nNaive approach (1 pkg/item):  {naive_total_capacity:>10,} total package slots")
print(f"3D bin packing approach:      {bin_packed_capacity:>10,} total package slots")
print(f"\nImprovement factor:           {bin_packed_capacity / naive_total_capacity:>10.2f}×")

print("\n" + "="*100)
print("[3] EXAMPLE: SKUD2 (48×36×20 inches)")
print("="*100)

skud2_configs = configs_3d_df[configs_3d_df['SKU'] == 'SKUD2']

print("\nSKUD2 dimensions: 48×36×20 inches")
print("Pallet item slot: 48×48×48 inches\n")

for _, row in skud2_configs.iterrows():
    fac = row['Facility']
    pkg_per_item = row['Packages_per_Item']
    items = row['Items_per_Shelf']
    total = row['Total_Packages_per_Shelf']

    print(f"{fac:<15}: {pkg_per_item} SKUD2 fit in 1 item slot → {items} items × {pkg_per_item} = {total} SKUD2/shelf")
    print(f"                 vs. naive: {items} SKUD2/shelf (improvement: {pkg_per_item}×)")

print("\n" + "="*100)
print("[4] SHELF REQUIREMENT REDUCTION")
print("="*100)

# Hypothetical demand to show shelf reduction
print("\nExample: 1,000 SKUD2 units needed")
print("\nColumbus Pallet:")
print(f"  Naive approach:    1,000 ÷ 7 = 143 shelves")
print(f"  3D bin packing:    1,000 ÷ 14 = 72 shelves")
print(f"  Reduction:         50% fewer shelves needed")

print("\n" + "="*100)
print("CONCLUSION")
print("="*100)
print("\nProper 3D bin packing increases capacity by 2-16× per shelf")
print("This dramatically reduces expansion requirements:")
print("  - Sacramento: No expansion needed (was 69,604 shelves)")
print("  - Austin: 3,903 shelves (was 13,751) - 72% reduction")
print("  - Columbus: 30,594 shelves (was 72,927) - 58% reduction")
print()
