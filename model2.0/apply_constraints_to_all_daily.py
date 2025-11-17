"""
Apply 93% capacity and pallet expansion limits to all DAILY models
"""
import re
from pathlib import Path
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Files to update
files_to_update = [
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_0_0_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_5_2_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_10_3_doh.py"
]

# Constants to add
MAX_PALLET_SAC = 2810
MAX_PALLET_AUSTIN = 2250

for file_path in files_to_update:
    print(f"\nProcessing {Path(file_path).name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already updated
    if 'MAX_PALLET_EXPANSION_SAC' in content:
        print(f"  ✓ Already has pallet expansion limits")
    else:
        # Add pallet expansion limits after curr_shelves_param
        pattern = r'(curr_shelves_param = Parameter\(m, name="curr_shelves", domain=\[f, st\], records=curr_shelves_records\))'
        replacement = r'''\1

# Config volume parameter
config_volume_records = [(str(cid), config_volume[cid]) for cid in config_ids]
config_volume_param = Parameter(m, name="config_volume", domain=c, records=config_volume_records)

# Warehouse volume capacity at 93% (cu ft)
warehouse_cap_records = [(fac, warehouse_volume_cap[fac]) for fac in facilities]
warehouse_cap_param = Parameter(m, name="warehouse_cap", domain=f, records=warehouse_cap_records)

# Pallet expansion limits
MAX_PALLET_EXPANSION_SAC = 2810  # Maximum additional pallet shelves for Sacramento
MAX_PALLET_EXPANSION_AUSTIN = 2250  # Maximum additional pallet shelves for Austin'''
        content = re.sub(pattern, replacement, content, count=1)
        print(f"  ✓ Added pallet expansion limits and volume parameters")

    # Check if slack variables added
    if 'slack_pallet_expansion_sac' in content:
        print(f"  ✓ Already has pallet expansion slack variables")
    else:
        # Add slack variables after slack_shelf_austin
        pattern = r'(slack_shelf_austin = Variable\(m, name="slack_shelf_austin", domain=st, type="positive"\))'
        replacement = r'''\1
slack_pallet_expansion_sac = Variable(m, name="slack_pallet_expansion_sac", type="positive")
slack_pallet_expansion_austin = Variable(m, name="slack_pallet_expansion_austin", type="positive")
slack_volume_cap = Variable(m, name="slack_volume_cap", domain=[t_month, t_day, f], type="positive")'''
        content = re.sub(pattern, replacement, content, count=1)
        print(f"  ✓ Added slack variables")

    # Update objective function
    if 'slack_pallet_expansion_sac * 500' in content:
        print(f"  ✓ Objective already includes new slack variables")
    else:
        # Update objective to include new slacks
        pattern = r'(total_slack ==\s+Sum\(\[t_month, t_day, s\], slack_demand\[t_month, t_day, s\] \* 1000\) \+\s+Sum\(\[t_month, t_day, s, f\], slack_doh\[t_month, t_day, s, f\] \* 10\) \+\s+Sum\(st, slack_shelf_sac\[st\] \* 100\) \+\s+Sum\(st, slack_shelf_austin\[st\] \* 100\))'
        replacement = r'''total_slack ==
    Sum([t_month, t_day, s], slack_demand[t_month, t_day, s] * 1000) +
    Sum([t_month, t_day, s, f], slack_doh[t_month, t_day, s, f] * 10) +
    Sum(st, slack_shelf_sac[st] * 100) +
    Sum(st, slack_shelf_austin[st] * 100) +
    slack_pallet_expansion_sac * 500 +
    slack_pallet_expansion_austin * 500 +
    Sum([t_month, t_day, f], slack_volume_cap[t_month, t_day, f] * 50)'''
        content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE | re.DOTALL)
        print(f"  ✓ Updated objective function")

    # Add volume capacity constraint
    if 'volume_capacity = Equation' in content:
        print(f"  ✓ Volume capacity constraint already exists")
    else:
        # Add volume capacity and pallet expansion constraints after shelf_limit_columbus
        pattern = r'(shelf_limit_columbus = Equation\(m, name="shelf_limit_columbus", domain=st\)\nshelf_limit_columbus\[st\] = \(\s+Sum\(c, shelves_per_config\[c\] \* config_fac_param\[c, "Columbus"\] \* config_st_param\[c, st\]\) <=\s+curr_shelves_param\["Columbus", st\]\n\))'
        replacement = r'''\1

# 93% warehouse volume capacity constraint (applies to total warehouse, not set packing)
volume_capacity = Equation(m, name="volume_capacity", domain=[t_month, t_day, f])
volume_capacity[t_month, t_day, f] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, f] * config_volume_param[c]) <=
    warehouse_cap_param[f] + slack_volume_cap[t_month, t_day, f]
)

# Pallet expansion limits with slack variables
pallet_expansion_limit_sac = Equation(m, name="pallet_expansion_limit_sac")
pallet_expansion_limit_sac[...] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Sacramento"] * config_st_param[c, "Pallet"]) <=
    curr_shelves_param["Sacramento", "Pallet"] + MAX_PALLET_EXPANSION_SAC + slack_pallet_expansion_sac
)

pallet_expansion_limit_austin = Equation(m, name="pallet_expansion_limit_austin")
pallet_expansion_limit_austin[...] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Austin"] * config_st_param[c, "Pallet"]) <=
    curr_shelves_param["Austin", "Pallet"] + MAX_PALLET_EXPANSION_AUSTIN + slack_pallet_expansion_austin
)'''
        content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE | re.DOTALL)
        print(f"  ✓ Added volume capacity and pallet expansion constraints")

    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ File updated successfully")

print("\n" + "="*80)
print("ALL FILES UPDATED SUCCESSFULLY")
print("="*80)
print("\nChanges applied:")
print("  1. 93% warehouse volume capacity constraint for all facilities")
print("  2. Pallet expansion limits: Sacramento = 2810, Austin = 2250")
print("  3. Slack variables for constraint violations")
print("  4. Updated objective function to penalize slack")
