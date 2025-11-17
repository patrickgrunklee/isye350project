"""
Apply 93% cap per storage type to all remaining DAILY models
Mirrors the changes made to phase2_DAILY_3_1_doh.py
"""
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

files_to_update = [
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_0_0_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_5_2_doh.py",
    r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_10_3_doh.py"
]

# Read the reference file to get the exact constraint text
reference_file = r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\phase2_DAILY_3_1_doh.py"
with open(reference_file, 'r', encoding='utf-8') as f:
    ref_lines = f.readlines()

# Find the new 93% utilization constraints in the reference
new_constraints = []
capture = False
for i, line in enumerate(ref_lines):
    if '# 93% utilization cap per storage type' in line:
        capture = True
    if capture:
        new_constraints.append(line)
        if 'print("   ✓ Constraints created' in line:
            break

new_constraints_text = ''.join(new_constraints)

for file_path in files_to_update:
    print(f"\nProcessing {Path(file_path).name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove shelving_dims_df loading and volume calculations
    print("  - Removing warehouse volume calculations...")
    # Find the section and replace
    import re

    # Remove shelving dimensions loading and volume tracking
    pattern = r'# Load current shelves\nprint\("\\n\[5/8\] Loading current shelving capacity\.\.\."\)\nshelving_dims_df = pd\.read_csv.*?print\(f"   ✓ Current shelves loaded"\)'
    replacement = '''# Load current shelves
print("\\n[5/8] Loading current shelving capacity...")
curr_shelves = {}
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
    curr_shelves[(fac, st)] = int(row['Number of Shelves'])

print(f"   ✓ Current shelves loaded")'''
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # 2. Remove config_volume tracking
    print("  - Removing config volume tracking...")
    content = content.replace('config_volume = {}  # Track volume per config', '')
    content = content.replace('        config_volume[cid] = 0  # Initialize volume', '')
    content = re.sub(r'    # Add volume for this SKU in this config.*?\n', '', content)
    content = content.replace('    config_volume[cid] += total_units * sku_data[sku][\'sell_volume\']', '')
    content = content.replace('print(f"   ✓ Volume calculated for each configuration")', '')

    # 3. Remove volume parameters
    print("  - Removing volume parameters...")
    content = re.sub(r'# Config volume parameter\n.*?config_volume_param.*?\n\n', '', content, flags=re.DOTALL)
    content = re.sub(r'# Warehouse volume capacity.*?\nwarehouse_cap_param.*?\n\n', '', content, flags=re.DOTALL)
    content = content.replace('print("   ✓ Slack variables for pallet expansion limits and 93% volume capacity")',
                            'print("   ✓ Slack variables for pallet expansion limits")')

    # 4. Remove slack_volume_cap variable
    print("  - Removing slack_volume_cap variable...")
    content = content.replace('slack_volume_cap = Variable(m, name="slack_volume_cap", domain=[t_month, t_day, f], type="positive")\n', '')

    # 5. Remove volume slack from objective
    print("  - Removing volume slack from objective...")
    content = content.replace('    Sum([t_month, t_day, f], slack_volume_cap[t_month, t_day, f] * 50)\n', '')
    # Fix objective to remove trailing +
    content = re.sub(r'(slack_pallet_expansion_austin \* 500) \+\n\)', r'\1\n)', content)

    # 6. Remove volume_capacity constraint
    print("  - Removing volume capacity constraint...")
    content = re.sub(r'# 93% warehouse volume capacity constraint.*?\n\n# Pallet expansion limits', '# Pallet expansion limits', content, flags=re.DOTALL)

    # 7. Replace 99% utilization constraints with 93% per storage type
    print("  - Replacing utilization constraints...")
    pattern = r'# 99% utilization constraints.*?austin_utilization\[...\] = \(.*?\)'
    content = re.sub(pattern, new_constraints_text.rstrip(), content, flags=re.DOTALL)

    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ File updated successfully")

print("\n" + "="*80)
print("ALL FILES UPDATED")
print("="*80)
print("\nChanges:")
print("  1. Removed warehouse volume capacity constraints")
print("  2. Replaced 99% pallet utilization with 93% cap per storage type")
print("  3. 93% cap applies to ALL storage types (Bins, Racking, Pallet, Hazmat)")
print("  4. Kept pallet expansion limits (Sacramento: 2810, Austin: 2250)")
