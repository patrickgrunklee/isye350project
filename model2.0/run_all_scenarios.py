"""
Run multiple DoH scenarios in batch
"""
import subprocess
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Define all scenarios to run (domestic, international)
scenarios = [
    {"doh_intl": 0, "doh_dom": 0, "name": "0_0_doh"},
    {"doh_intl": 3, "doh_dom": 1, "name": "3_1_doh"},
    {"doh_intl": 6, "doh_dom": 2, "name": "6_2_doh"},
    {"doh_intl": 8, "doh_dom": 3, "name": "8_3_doh"},
    {"doh_intl": 10, "doh_dom": 4, "name": "10_4_doh"},
    {"doh_intl": 12, "doh_dom": 5, "name": "12_5_doh"},
    {"doh_intl": 15, "doh_dom": 7, "name": "15_7_doh"},
    {"doh_intl": 17, "doh_dom": 9, "name": "17_9_doh"},
    {"doh_intl": 19, "doh_dom": 11, "name": "19_11_doh"},
    {"doh_intl": 21, "doh_dom": 14, "name": "21_14_doh"},
]

print("="*80)
print("RUNNING ALL DOH SCENARIOS")
print("="*80)
print(f"\nTotal scenarios: {len(scenarios)}")
for s in scenarios:
    print(f"  - {s['name']}: International {s['doh_intl']} days, Domestic {s['doh_dom']} days")
print()

failed_scenarios = []

for i, scenario in enumerate(scenarios, 1):
    print("\n" + "="*80)
    print(f"SCENARIO {i}/{len(scenarios)}: {scenario['name']}")
    print("="*80)

    cmd = [
        "python",
        "phase2_DAILY_parameterized.py",
        "--doh_intl", str(scenario['doh_intl']),
        "--doh_dom", str(scenario['doh_dom']),
        "--scenario_name", scenario['name']
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✓ {scenario['name']} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {scenario['name']} FAILED with error code {e.returncode}")
        failed_scenarios.append(scenario['name'])
    except Exception as e:
        print(f"\n✗ {scenario['name']} FAILED: {e}")
        failed_scenarios.append(scenario['name'])

print("\n" + "="*80)
print("BATCH RUN COMPLETE")
print("="*80)
print(f"\nSuccessful: {len(scenarios) - len(failed_scenarios)}/{len(scenarios)}")
if failed_scenarios:
    print(f"Failed scenarios: {', '.join(failed_scenarios)}")
else:
    print("✓ All scenarios completed successfully!")
