"""
Update all DAILY models to use 93% cap per storage type (not volume)
Changes:
1. Remove volume capacity constraint and slack variables
2. Replace 99% pallet utilization with 93% utilization for ALL storage types
3. Keep pallet expansion limits
"""
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

files_to_update = [
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_0_0_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_3_1_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_5_2_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_10_3_doh.py"
]

for file_path in files_to_update:
    print(f"\nProcessing {Path(file_path).name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_until = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip volume capacity calculation section
        if '# Calculate total warehouse volume capacity' in line:
            print("  - Removing warehouse volume capacity calculation")
            # Skip until we find the next major section
            while i < len(lines) and '# Process configs' not in lines[i]:
                i += 1
            i -= 1  # Back up one so we keep the Process configs line
            i += 1
            continue

        # Skip warehouse volume parameters
        if 'warehouse_volume_cap = {}' in line or 'shelf_volume = {}' in line:
            i += 1
            continue

        # Skip shelving_dims_df loading if not already skipped
        if 'shelving_dims_df = pd.read_csv' in line:
            i += 1
            continue

        # Skip shelf_volume dict operations
        if 'shelf_volume[' in line:
            i += 1
            continue

        # Skip warehouse_volume_cap dict operations
        if 'warehouse_volume_cap[' in line:
            i += 1
            continue

        # Skip config_volume tracking
        if 'config_volume = {}' in line:
            i += 1
            continue
        if 'config_volume[cid]' in line:
            i += 1
            continue
        if '✓ Volume calculated for each configuration' in line:
            i += 1
            continue

        # Skip volume parameter creation
        if 'config_volume_records' in line or 'config_volume_param' in line:
            i += 1
            continue
        if 'warehouse_cap_records' in line or 'warehouse_cap_param' in line:
            i += 1
            continue
        if 'Warehouse volume capacity' in line and '93%' in line:
            # Skip the print statements about warehouse volume
            while i < len(lines) and ('print(f"      {fac}:' in lines[i] or 'for fac in facilities:' in lines[i]):
                i += 1
            continue

        # Remove slack_volume_cap variable
        if 'slack_volume_cap = Variable' in line:
            print("  - Removing slack_volume_cap variable")
            i += 1
            continue

        # Update objective function - remove volume slack term
        if 'Sum([t_month, t_day, f], slack_volume_cap' in line:
            print("  - Removing slack_volume_cap from objective")
            i += 1
            continue

        # Remove volume_capacity constraint entirely
        if '# 93% warehouse volume capacity constraint' in line:
            print("  - Removing volume capacity constraint")
            # Skip until pallet expansion limits
            while i < len(lines) and '# Pallet expansion limits' not in lines[i]:
                i += 1
            i -= 1
            i += 1
            continue

        # Replace 99% utilization constraints with 93% per storage type
        if '# 99% utilization constraints' in line:
            print("  - Replacing 99% pallet utilization with 93% per storage type")
            new_lines.append('# 93% utilization cap per storage type\n')
            new_lines.append('# Columbus (cannot expand)\n')
            new_lines.append('utilization_cap_columbus = Equation(m, name="utilization_cap_columbus", domain=st)\n')
            new_lines.append('utilization_cap_columbus[st] = (\n')
            new_lines.append('    Sum(c, shelves_per_config[c] * config_fac_param[c, "Columbus"] * config_st_param[c, st]) <=\n')
            new_lines.append('    0.93 * curr_shelves_param["Columbus", st]\n')
            new_lines.append(')\n')
            new_lines.append('\n')
            new_lines.append('# Sacramento (with expansion)\n')
            new_lines.append('utilization_cap_sac = Equation(m, name="utilization_cap_sac", domain=st)\n')
            new_lines.append('utilization_cap_sac[st] = (\n')
            new_lines.append('    Sum(c, shelves_per_config[c] * config_fac_param[c, "Sacramento"] * config_st_param[c, st]) <=\n')
            new_lines.append('    0.93 * (curr_shelves_param["Sacramento", st] + slack_shelf_sac[st])\n')
            new_lines.append(')\n')
            new_lines.append('\n')
            new_lines.append('# Austin (with expansion)\n')
            new_lines.append('utilization_cap_austin = Equation(m, name="utilization_cap_austin", domain=st)\n')
            new_lines.append('utilization_cap_austin[st] = (\n')
            new_lines.append('    Sum(c, shelves_per_config[c] * config_fac_param[c, "Austin"] * config_st_param[c, st]) <=\n')
            new_lines.append('    0.93 * (curr_shelves_param["Austin", st] + slack_shelf_austin[st])\n')
            new_lines.append(')\n')
            new_lines.append('\n')

            # Skip old utilization constraints
            while i < len(lines) and 'print("   ✓ Constraints created' not in lines[i]:
                i += 1
            i -= 1
            i += 1
            continue

        new_lines.append(line)
        i += 1

    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"  ✓ File updated successfully")

print("\n" + "="*80)
print("ALL FILES UPDATED")
print("="*80)
print("\nChanges:")
print("  1. Removed warehouse volume capacity constraints")
print("  2. Replaced 99% pallet utilization with 93% cap per storage type")
print("  3. 93% cap applies to: Bins, Racking, Pallet, Hazmat")
print("  4. Kept pallet expansion limits (Sacramento: 2810, Austin: 2250)")
