"""
Compare OLD vs NEW shelf weight capacities
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*120)
print("SHELF CAPACITY COMPARISON: OLD (INCORRECT) vs NEW (CORRECTED)")
print("="*120)

print("\nKEY INSIGHT: Weight limit applies PER ITEM, not per shelf!")
print("Total Shelf Weight Capacity = (Max Items/Shelf) × (Weight per Item)")

comparisons = [
    {
        'facility': 'Columbus',
        'storage': 'Pallet',
        'max_items': 7,
        'weight_per_item': 600,
        'old_total': 600,
        'new_total': 7 * 600
    },
    {
        'facility': 'Austin',
        'storage': 'Pallet',
        'max_items': 6,
        'weight_per_item': 600,
        'old_total': 600,
        'new_total': 6 * 600
    },
    {
        'facility': 'Sacramento',
        'storage': 'Pallet',
        'max_items': 4,
        'weight_per_item': 600,
        'old_total': 600,
        'new_total': 4 * 600
    },
    {
        'facility': 'Columbus',
        'storage': 'Bins',
        'max_items': 1,
        'weight_per_item': 60,
        'old_total': 66.14,
        'new_total': 1 * 60
    },
    {
        'facility': 'Austin',
        'storage': 'Bins',
        'max_items': 3,
        'weight_per_item': 30,
        'old_total': 30,
        'new_total': 3 * 30
    },
    {
        'facility': 'Sacramento',
        'storage': 'Bins',
        'max_items': 3,
        'weight_per_item': 30,
        'old_total': 30,
        'new_total': 3 * 30
    },
    {
        'facility': 'Columbus',
        'storage': 'Racking',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    },
    {
        'facility': 'Austin',
        'storage': 'Racking',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    },
    {
        'facility': 'Sacramento',
        'storage': 'Racking',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    },
    {
        'facility': 'Columbus',
        'storage': 'Hazmat',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    },
    {
        'facility': 'Austin',
        'storage': 'Hazmat',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    },
    {
        'facility': 'Sacramento',
        'storage': 'Hazmat',
        'max_items': 8,
        'weight_per_item': 100,
        'old_total': 100,
        'new_total': 8 * 100
    }
]

print("\n" + "="*120)
print(f"{'Facility':<15} {'Storage':<12} {'Max Items':<12} {'Weight/Item':<15} {'OLD Total':<15} {'NEW Total':<15} {'Multiplier':<12}")
print("="*120)

for comp in comparisons:
    multiplier = comp['new_total'] / comp['old_total'] if comp['old_total'] > 0 else 0

    print(f"{comp['facility']:<15} {comp['storage']:<12} {comp['max_items']:<12} {comp['weight_per_item']:<15.0f} {comp['old_total']:<15.2f} {comp['new_total']:<15.2f} {multiplier:<12.1f}×")

print("="*120)

print("\n" + "="*120)
print("IMPACT ON PHASE 1 CONFIGURATIONS")
print("="*120)

print("\nExample: Austin Hazmat shelf")
print("  OLD interpretation:")
print("    - Total shelf capacity: 100 lbs")
print("    - SKUA1 packages: 2 lbs each")
print("    - Max packages: 100 / 2 = 50 packages")
print("    - Config 11 OLD: 50× SKUA1 = 100 lbs total")

print("\n  NEW (CORRECT) interpretation:")
print("    - Max items per shelf: 8 (but 999,999 for Hazmat in practice)")
print("    - Weight per item: 100 lbs")
print("    - Total shelf capacity: 8 × 100 = 800 lbs (or effectively unlimited for Hazmat)")
print("    - SKUA1 packages: 2 lbs each")
print("    - Max packages: 800 / 2 = 400 packages")
print("    - Config 11 NEW: 400× SKUA1 = 800 lbs total")
print("    - INCREASE: 8× more packages per shelf!")

print("\nExample: Columbus Pallet shelf")
print("  OLD interpretation:")
print("    - Total shelf capacity: 600 lbs")
print("    - SKUD2 (desk): 75 lbs each")
print("    - Max packages: 600 / 75 = 8 packages")
print("    - But package limit is 7, so: 7 packages max")
print("    - Config 42 OLD: 7× SKUD2 = 525 lbs total (87.5% utilization)")

print("\n  NEW (CORRECT) interpretation:")
print("    - Max items per shelf: 7")
print("    - Weight per item: 600 lbs")
print("    - Total shelf capacity: 7 × 600 = 4,200 lbs")
print("    - SKUD2 (desk): 75 lbs each")
print("    - Max packages: 4,200 / 75 = 56 packages")
print("    - But package limit is 7, so: 7 packages max (unchanged)")
print("    - Config 42 NEW: 7× SKUD2 = 525 lbs total (12.5% utilization)")
print("    - CAPACITY INCREASE: 7× more weight capacity per shelf!")
print("    - NOTE: Package count unchanged because limited by max items (7), not weight")

print("\n" + "="*120)
print("KEY TAKEAWAYS")
print("="*120)
print("\n1. MAX ITEMS PER SHELF stays the same (physical constraint)")
print("   - Columbus Pallet: 7 items")
print("   - Austin Pallet: 6 items")
print("   - Sacramento Pallet: 4 items")

print("\n2. WEIGHT CAPACITY PER SHELF increased 3-8×")
print("   - Pallets: 3,600-4,200 lbs (was 600 lbs)")
print("   - Bins: 60-90 lbs (was 30-66 lbs)")
print("   - Racking: 800 lbs (was 100 lbs)")
print("   - Hazmat: 800 lbs (was 100 lbs)")

print("\n3. PACKAGE COUNT per shelf:")
print("   - For LIGHT items (e.g., SKUA1 @ 2 lbs): INCREASED 8× (50 → 400 packages)")
print("   - For HEAVY items (e.g., SKUD2 @ 75 lbs): UNCHANGED (still limited by max items)")
print("   - Pallet configs: Still 4-7 packages max (physical item limit)")
print("   - Hazmat configs: 50 → 400 packages (weight was bottleneck)")

print("\n4. PHASE 2 SLACK ANALYSIS results unchanged because:")
print("   - Problem is NUMBER OF SHELVES needed (72,927 more Columbus Pallet shelves)")
print("   - Not weight capacity per shelf")
print("   - More weight per shelf doesn't help if you don't have enough shelves!")

print("\n" + "="*120)
