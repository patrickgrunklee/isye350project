"""
Update all DAILY models with enhanced supplier tracking:
1. Track by specific supplier company name (not just Domestic/International)
2. Add truck utilization metrics
3. Add low utilization analysis

This script reads phase2_DAILY_3_1_doh.py as the template and applies
the truckload analysis section to the other models.
"""

import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

MODEL_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0")

# Models to update (excluding 3_1 which is the template)
models_to_update = [
    'phase2_DAILY_0_0_doh.py',
    'phase2_DAILY_5_2_doh.py',
    'phase2_DAILY_10_3_doh.py'
]

print("="*80)
print("UPDATING SUPPLIER TRACKING IN PHASE2 DAILY MODELS")
print("="*80)

# Read the template (3_1_doh) to extract the truckload analysis section
template_path = MODEL_DIR / 'phase2_DAILY_3_1_doh.py'
with open(template_path, 'r', encoding='utf-8') as f:
    template_content = f.read()

# Extract the imports
new_imports = '''from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    SKU_TO_SUPPLIER,
    SKU_TO_SUPPLIER_TYPE,
    SUPPLIERS,
    calculate_truckloads,
    calculate_truck_utilization
)'''

# Extract the truckload analysis section (from "# Calculate truckloads" to end of analysis)
start_marker = "# Calculate truckloads per supplier per day per facility"
end_marker = "# Save truckload analysis to CSV"

start_idx = template_content.find(start_marker)
end_idx = template_content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Could not find truckload analysis section in template")
    sys.exit(1)

# Get the full analysis section including the save part
end_of_save = template_content.find('print("\\n⚠️  No deliveries found in model solution")', end_idx)
truckload_analysis = template_content[start_idx:end_of_save + len('print("\\n⚠️  No deliveries found in model solution")')]

print(f"\nExtracted {len(truckload_analysis)} characters of truckload analysis from template")

for model_file in models_to_update:
    model_path = MODEL_DIR / model_file

    print(f"\n Processing {model_file}...")

    if not model_path.exists():
        print(f"  ⚠️  File not found: {model_path}")
        continue

    # Read file
    with open(model_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update imports
    old_imports = '''from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    SUPPLIER_MAP,
    calculate_truckloads
)'''

    if old_imports in content:
        content = content.replace(old_imports, new_imports)
        print(f"  ✓ Updated imports")
    else:
        print(f"  ℹ️  Imports already updated or not found")

    # 2. Replace the entire truckload analysis section
    old_start = "# Calculate truckloads per supplier per day per facility"
    old_end = 'print("\\n⚠️  No deliveries found in model solution")'

    old_start_idx = content.find(old_start)
    old_end_idx = content.find(old_end)

    if old_start_idx != -1 and old_end_idx != -1:
        # Replace the entire section
        before = content[:old_start_idx]
        after = content[old_end_idx + len(old_end):]
        content = before + truckload_analysis + after
        print(f"  ✓ Replaced truckload analysis section")
    else:
        print(f"  ⚠️  Could not find truckload analysis section to replace")
        continue

    # Write updated content
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ Successfully updated {model_file}")

print("\n" + "="*80)
print("UPDATE COMPLETE")
print("="*80)
print("\nUpdated models with enhanced supplier tracking:")
for model_file in models_to_update:
    print(f"  - {model_file}")
print("\nEnhancements added:")
print("  ✓ Track by specific supplier company name")
print("  ✓ Calculate weight and volume utilization percentages")
print("  ✓ Identify binding constraints (weight vs volume)")
print("  ✓ Detect low utilization deliveries (<50%)")
print("  ✓ Per-supplier statistics")
