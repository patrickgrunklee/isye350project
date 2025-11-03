"""
RUN ALL DOH POLICIES WITH COLUMBUS 99% UTILIZATION CONSTRAINT

Runs three scenarios:
1. 10/3 business days DoH (International/Domestic)
2. 5/2 business days DoH
3. 3/1 business days DoH

Each enforces Columbus at 99%+ utilization if Sac/Austin need expansion
"""

import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*100)
print("RUNNING ALL DOH POLICY SCENARIOS")
print("="*100)
print("\nConstraint: Columbus must be at 99%+ pallet utilization if Sac/Austin expand")
print()

scenarios = [
    {
        'name': '10/3 Business Days DoH',
        'lead_time_file': 'Lead TIme_14_3_business_days.csv',
        'intl_days': 10,
        'domestic_days': 3
    },
    {
        'name': '5/2 Business Days DoH',
        'lead_time_file': 'Lead TIme_5_2_business_days.csv',
        'intl_days': 5,
        'domestic_days': 2
    },
    {
        'name': '3/1 Business Days DoH',
        'lead_time_file': 'Lead TIme_3_1_business_days.csv',
        'intl_days': 3,
        'domestic_days': 1
    }
]

results = []

for scenario in scenarios:
    print("="*100)
    print(f"SCENARIO: {scenario['name']}")
    print(f"  International: {scenario['intl_days']} business days")
    print(f"  Domestic: {scenario['domestic_days']} business days")
    print("="*100)
    print()

    # Update the main model file to use this lead time file
    model_file = r"c:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\phase2_pure_sku_shelves.py"

    with open(model_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace lead time file
    for s in scenarios:
        content = content.replace(
            f'lead_time_df = pd.read_csv(DATA_DIR / "{s["lead_time_file"]}")',
            f'lead_time_df = pd.read_csv(DATA_DIR / "{scenario["lead_time_file"]}")'
        )

    # Update title
    content = content.replace(
        'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - 3/1 DAYS-ON-HAND',
        f'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - {scenario["intl_days"]}/{scenario["domestic_days"]} DAYS-ON-HAND'
    )
    content = content.replace(
        'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - 5/2 DAYS-ON-HAND',
        f'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - {scenario["intl_days"]}/{scenario["domestic_days"]} DAYS-ON-HAND'
    )
    content = content.replace(
        'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - 10/3 DAYS-ON-HAND',
        f'PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - {scenario["intl_days"]}/{scenario["domestic_days"]} DAYS-ON-HAND'
    )

    # Update DoH in print statement
    content = content.replace(
        '  - International: 3 business days | Domestic: 1 business day',
        f'  - International: {scenario["intl_days"]} business days | Domestic: {scenario["domestic_days"]} business days'
    )
    content = content.replace(
        '  - International: 5 business days | Domestic: 2 business days',
        f'  - International: {scenario["intl_days"]} business days | Domestic: {scenario["domestic_days"]} business days'
    )
    content = content.replace(
        '  - International: 10 business days | Domestic: 3 business days',
        f'  - International: {scenario["intl_days"]} business days | Domestic: {scenario["domestic_days"]} business days'
    )

    with open(model_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # Run the model
    result = subprocess.run(
        ['python', model_file],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    print("\n")

print("="*100)
print("ALL SCENARIOS COMPLETE")
print("="*100)
