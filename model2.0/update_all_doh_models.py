"""
Update all DoH models to use continuous packing with max items limit
"""
import re

files = [
    'phase2_pure_sku_shelves_0_0_doh_ALL99pct.py',
    'phase2_pure_sku_shelves_5_2_doh_ALL99pct.py',
    'phase2_pure_sku_shelves_10_3_doh_ALL99pct.py'
]

old_pattern = '''# Generate PURE-SKU packing configurations
print("\\n[6/7] Generating pure-SKU packing configurations...")
print("   Pure-SKU = entire shelf dedicated to one SKU")
print("   - Most SKUs: Discrete item-based packing (respects max items/shelf)")
print("   - Chairs & Desks: Continuous volume-based packing (no item limits)")

# Define furniture SKUs that should use continuous packing
furniture_skus = ['SKUC1', 'SKUC2', 'SKUD1', 'SKUD2', 'SKUD3']

pure_sku_configs = []
config_id = packing_configs_df['Config_ID'].max() + 1

for fac in facilities:
    for st in storage_types:
        specs = shelf_specs.get((fac, st))
        if specs is None or specs['volume'] is None:
            continue

        shelf_vol = specs['volume']
        shelf_weight = specs['weight_limit']
        max_items = specs['max_items']

        # For each SKU, calculate pure-SKU capacity
        for sku in skus:
            pkg_vol = sku_data[sku]['sell_volume']
            pkg_weight = sku_data[sku]['sell_weight']

            # Chairs and Desks: Use continuous packing (volume/weight only)
            if sku in furniture_skus:
                by_volume = int(shelf_vol / pkg_vol)
                by_weight = int(shelf_weight / pkg_weight)
                max_packages = min(by_volume, by_weight)

                if max_packages > 0:
                    pure_sku_configs.append({
                        'Config_ID': config_id,
                        'Facility': fac,
                        'Storage_Type': st,
                        'SKU': sku,
                        'Packages_per_Item': max_packages,
                        'Items_per_Shelf': 1,
                        'Total_Packages_per_Shelf': max_packages,
                        'Weight_per_Package': pkg_weight,
                        'Total_Weight': max_packages * pkg_weight,
                        'Units_per_Package': 1,
                        'Config_Type': 'Pure_SKU_Continuous_Furniture'
                    })
                    config_id += 1

            # All other SKUs: Use discrete item-based packing
            else:
                # Calculate max packages per item (respecting weight limit per item)
                weight_per_item = shelf_weight / max_items
                max_pkg_per_item_by_weight = int(weight_per_item / pkg_weight)

                # Also check volume constraint per item
                volume_per_item = shelf_vol / max_items
                max_pkg_per_item_by_volume = int(volume_per_item / pkg_vol)

                # Take minimum
                max_pkg_per_item = min(max_pkg_per_item_by_weight, max_pkg_per_item_by_volume)

                if max_pkg_per_item > 0:
                    total_packages = max_pkg_per_item * max_items
                    pure_sku_configs.append({
                        'Config_ID': config_id,
                        'Facility': fac,
                        'Storage_Type': st,
                        'SKU': sku,
                        'Packages_per_Item': max_pkg_per_item,
                        'Items_per_Shelf': max_items,
                        'Total_Packages_per_Shelf': total_packages,
                        'Weight_per_Package': pkg_weight,
                        'Total_Weight': total_packages * pkg_weight,
                        'Units_per_Package': 1,
                        'Config_Type': 'Pure_SKU_Discrete'
                    })
                    config_id += 1

# Combine with existing 3D bin packing configs (for mixed-SKU shelves)
furniture_count = sum(1 for cfg in pure_sku_configs if cfg['Config_Type'] == 'Pure_SKU_Continuous_Furniture')
discrete_count = sum(1 for cfg in pure_sku_configs if cfg['Config_Type'] == 'Pure_SKU_Discrete')
print(f"   ✓ Generated {len(pure_sku_configs)} pure-SKU configurations")
print(f"      - Discrete (items-based): {discrete_count}")
print(f"      - Continuous (furniture): {furniture_count}")'''

new_code = '''# Generate PURE-SKU continuous packing configurations
print("\\n[6/7] Generating pure-SKU continuous packing configurations...")
print("   Pure-SKU = entire shelf dedicated to one SKU (continuous packing)")
print("   Limited by: volume, weight, AND max items per shelf")

pure_sku_configs = []
config_id = packing_configs_df['Config_ID'].max() + 1

for fac in facilities:
    for st in storage_types:
        specs = shelf_specs.get((fac, st))
        if specs is None or specs['volume'] is None:
            continue

        shelf_vol = specs['volume']
        shelf_weight = specs['weight_limit']
        max_items = specs['max_items']

        # For each SKU, calculate pure-SKU continuous capacity
        for sku in skus:
            pkg_vol = sku_data[sku]['sell_volume']
            pkg_weight = sku_data[sku]['sell_weight']

            # Continuous packing: limited by volume, weight, AND max items
            by_volume = int(shelf_vol / pkg_vol)
            by_weight = int(shelf_weight / pkg_weight)
            by_items = max_items  # Cap at max items per shelf

            max_packages = min(by_volume, by_weight, by_items)

            if max_packages > 0:
                pure_sku_configs.append({
                    'Config_ID': config_id,
                    'Facility': fac,
                    'Storage_Type': st,
                    'SKU': sku,
                    'Packages_per_Item': max_packages,  # All packages treated as single item
                    'Items_per_Shelf': 1,
                    'Total_Packages_per_Shelf': max_packages,
                    'Weight_per_Package': pkg_weight,
                    'Total_Weight': max_packages * pkg_weight,
                    'Units_per_Package': 1,
                    'Config_Type': 'Pure_SKU_Continuous'
                })
                config_id += 1

# Combine with existing 3D bin packing configs (for mixed-SKU shelves)
print(f"   ✓ Generated {len(pure_sku_configs)} pure-SKU continuous configurations")'''

for filename in files:
    print(f"Updating {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    if old_pattern in content:
        content = content.replace(old_pattern, new_code)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Updated {filename}")
    else:
        print(f"  ✗ Pattern not found in {filename}")

print("\nDone!")
