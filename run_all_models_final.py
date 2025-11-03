"""
RUN ALL DOH MODELS WITH ALL-FACILITIES 99% UTILIZATION CONSTRAINT

Updates and runs all 4 DoH scenarios with the constraint that:
- If ANY facility needs expansion, then ALL facilities must be at 99%+ utilization
- This maximizes use of existing capacity system-wide
"""

import subprocess
import shutil
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Paths
MODEL_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model")
TEMPLATE = MODEL_DIR / "phase2_template_all_facilities_99pct.py"

scenarios = [
    {
        'name': '10/3 Business Days DoH',
        'lead_time_file': 'Lead TIme_14_3_business_days.csv',
        'output_file': 'phase2_pure_sku_shelves_10_3_doh_ALL99pct.py',
        'intl_days': 10,
        'domestic_days': 3,
        'title': '10/3 DAYS-ON-HAND'
    },
    {
        'name': '5/2 Business Days DoH',
        'lead_time_file': 'Lead TIme_5_2_business_days.csv',
        'output_file': 'phase2_pure_sku_shelves_5_2_doh_ALL99pct.py',
        'intl_days': 5,
        'domestic_days': 2,
        'title': '5/2 DAYS-ON-HAND'
    },
    {
        'name': '3/1 Business Days DoH',
        'lead_time_file': 'Lead TIme_3_1_business_days.csv',
        'output_file': 'phase2_pure_sku_shelves_3_1_doh_ALL99pct.py',
        'intl_days': 3,
        'domestic_days': 1,
        'title': '3/1 DAYS-ON-HAND'
    },
    {
        'name': '0/0 Business Days DoH (No Safety Stock)',
        'lead_time_file': 'Lead TIme_0_0_business_days.csv',
        'output_file': 'phase2_pure_sku_shelves_0_0_doh_ALL99pct.py',
        'intl_days': 0,
        'domestic_days': 0,
        'title': '0/0 DAYS-ON-HAND (NO SAFETY STOCK)'
    }
]

print("="*100)
print("UPDATING AND RUNNING ALL DOH MODELS")
print("="*100)
print("\nConstraint: ALL facilities at 99%+ pallet utilization if any expansion needed\n")

results_summary = []

for scenario in scenarios:
    print("="*100)
    print(f"SCENARIO: {scenario['name']}")
    print("="*100)

    # Copy template
    output_path = MODEL_DIR / scenario['output_file']
    shutil.copy(TEMPLATE, output_path)

    # Read and modify
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update lead time file
    content = content.replace(
        'Lead TIme_0_0_business_days.csv',
        scenario['lead_time_file']
    )

    # Update title
    content = content.replace(
        'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - 0/0 DAYS-ON-HAND (NO SAFETY STOCK)',
        f'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - {scenario["title"]}'
    )

    # Update description
    content = content.replace(
        '  - DoH = NO SAFETY STOCK (0 days on hand)\n  - International: 0 business days | Domestic: 0 business days\n  - Just-in-time inventory (only hold what\'s needed for monthly shipments)',
        f'  - DoH = Traditional safety stock (days of demand coverage)\n  - International: {scenario["intl_days"]} business days | Domestic: {scenario["domestic_days"]} business days'
    )

    # Save modified file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n✓ Created {scenario['output_file']}")
    print(f"  Running model...\n")

    # Run the model
    result = subprocess.run(
        ['python', str(output_path)],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    # Parse output for key results
    output_lines = result.stdout.split('\n')

    columbus_util = None
    sac_util = None
    austin_util = None
    sac_expansion = 0
    austin_expansion = 0

    for i, line in enumerate(output_lines):
        if 'Columbus:' in line and 'HARD CONSTRAINT' in line:
            # Next line should have utilization
            if i + 1 < len(output_lines) and '% utilization)' in output_lines[i+1]:
                util_line = output_lines[i+1]
                if '(' in util_line and '%' in util_line:
                    columbus_util = util_line.split('(')[1].split('%')[0].strip()

        if 'Sacramento:' in line and 'Pallet shelves used:' in output_lines[i]:
            if '(' in line and '%' in line:
                sac_util = line.split('(')[1].split('%')[0].strip()

        if 'Austin:' in line and i + 1 < len(output_lines) and 'Pallet shelves used:' in output_lines[i+1]:
            util_line = output_lines[i+1]
            if '(' in util_line and '%' in util_line:
                austin_util = util_line.split('(')[1].split('%')[0].strip()

        if 'Sacramento:' in line and i + 1 < len(output_lines):
            next_line = output_lines[i+1]
            if 'Pallet' in next_line and 'Need' in next_line:
                sac_expansion = int(next_line.split('Need')[1].split('more')[0].replace(',', '').strip())

        if 'Austin:' in line and i + 1 < len(output_lines):
            next_line = output_lines[i+1]
            if 'Pallet' in next_line and 'Need' in next_line:
                austin_expansion = int(next_line.split('Need')[1].split('more')[0].replace(',', '').strip())

    total_expansion = sac_expansion + austin_expansion

    results_summary.append({
        'name': scenario['name'],
        'columbus_util': columbus_util,
        'sac_util': sac_util,
        'austin_util': austin_util,
        'sac_expansion': sac_expansion,
        'austin_expansion': austin_expansion,
        'total_expansion': total_expansion
    })

    print(f"\n{'='*100}")
    print(f"RESULTS SUMMARY: {scenario['name']}")
    print(f"{'='*100}")
    print(f"\nUtilization:")
    print(f"  Columbus: {columbus_util}%")
    print(f"  Sacramento: {sac_util}%")
    print(f"  Austin: {austin_util}%")
    print(f"\nExpansion Required:")
    print(f"  Sacramento: +{sac_expansion:,} shelves")
    print(f"  Austin: +{austin_expansion:,} shelves")
    print(f"  TOTAL: {total_expansion:,} shelves")
    print()

print("\n" + "="*100)
print("FINAL COMPARISON TABLE")
print("="*100)
print()
print(f"{'DoH Policy':<30} {'Columbus':<12} {'Sacramento':<15} {'Austin':<15} {'Total Expansion':<20}")
print("-" * 100)

for r in results_summary:
    col_str = f"{r['columbus_util']}%" if r['columbus_util'] else "N/A"
    sac_str = f"+{r['sac_expansion']:,}" if r['sac_expansion'] > 0 else "No exp"
    aus_str = f"+{r['austin_expansion']:,}" if r['austin_expansion'] > 0 else "No exp"

    print(f"{r['name']:<30} {col_str:<12} {sac_str:<15} {aus_str:<15} {r['total_expansion']:,}")

print("\n" + "="*100)
print("ALL MODELS COMPLETE")
print("="*100)
print("\nAll facilities enforced at 99%+ utilization if any expansion needed")
print("All models saved with '_ALL99pct' suffix")
