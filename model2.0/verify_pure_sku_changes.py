"""
Verify the pure SKU configuration changes:
- Most SKUs now use discrete item-based packing
- Furniture (chairs and desks) use continuous volume-based packing
"""
import pandas as pd
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load configurations
config_file = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking\packing_configurations_pure_sku.csv")
df = pd.read_csv(config_file)

print("="*100)
print("VERIFICATION: PURE-SKU CONFIGURATION CHANGES")
print("="*100)

print("\n1. CONFIGURATION TYPE BREAKDOWN:")
print("-"*100)
print(df['Config_Type'].value_counts())

print("\n\n2. COLUMBUS PALLET SHELF CAPACITY COMPARISON:")
print("-"*100)

columbus_pallet = df[(df['Facility'] == 'Columbus') & (df['Storage_Type'] == 'Pallet')]

print("\nDISCRETE PACKING (Non-furniture SKUs) - 7 items per shelf:")
discrete = columbus_pallet[columbus_pallet['Config_Type'] == 'Pure_SKU_Discrete']
for _, row in discrete.iterrows():
    print(f"  {row['SKU']:6} : {row['Packages_per_Item']:4.0f} pkg/item × {row['Items_per_Shelf']} items = {row['Total_Packages_per_Shelf']:5.0f} pkg/shelf")

print("\nCONTINUOUS PACKING (Furniture SKUs) - Volume/weight limited:")
furniture = columbus_pallet[columbus_pallet['Config_Type'] == 'Pure_SKU_Continuous_Furniture']
for _, row in furniture.iterrows():
    print(f"  {row['SKU']:6} : {row['Total_Packages_per_Shelf']:5.0f} pkg/shelf (continuous - no item limit)")

print("\n\n3. VERIFICATION SUMMARY:")
print("-"*100)

furniture_skus = ['SKUC1', 'SKUC2', 'SKUD1', 'SKUD2', 'SKUD3']
discrete_pure = df[df['Config_Type'] == 'Pure_SKU_Discrete']
continuous_furniture = df[df['Config_Type'] == 'Pure_SKU_Continuous_Furniture']

print(f"✓ Discrete pure-SKU configs: {len(discrete_pure)}")
print(f"✓ Continuous furniture configs: {len(continuous_furniture)}")

# Verify discrete configs use max_items properly
discrete_by_facility_storage = discrete_pure.groupby(['Facility', 'Storage_Type'])['Items_per_Shelf'].unique()
print("\nDiscrete configs - Items per shelf by facility/storage:")
for (fac, st), items in discrete_by_facility_storage.items():
    print(f"  {fac:12} {st:10} : {items[0]} items/shelf")

# Verify furniture configs are only for furniture SKUs
furniture_config_skus = continuous_furniture['SKU'].unique()
print(f"\nFurniture configs are for: {sorted(furniture_config_skus)}")
print(f"Expected furniture SKUs:    {sorted(furniture_skus)}")

if set(furniture_config_skus) == set(furniture_skus):
    print("✓ CORRECT: All furniture configs are for chairs and desks only")
else:
    print("✗ ERROR: Mismatch in furniture SKUs")

# Verify discrete configs do NOT include furniture
discrete_config_skus = discrete_pure['SKU'].unique()
furniture_in_discrete = [sku for sku in discrete_config_skus if sku in furniture_skus]
if len(furniture_in_discrete) == 0:
    print("✓ CORRECT: No furniture SKUs in discrete configs")
else:
    print(f"✗ ERROR: Found furniture in discrete: {furniture_in_discrete}")

print("\n" + "="*100)
