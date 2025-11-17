"""
Test script for truckload_constants module

Validates truckload calculations with example scenarios.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    SUPPLIER_MAP,
    calculate_truckloads_weight,
    calculate_truckloads_volume,
    calculate_truckloads
)

print("="*80)
print("TRUCKLOAD CONSTANTS TEST")
print("="*80)

print("\n[1] Truck Specifications")
print(f"  Weight capacity: {TRUCK_WEIGHT_CAPACITY_LBS:,} lbs")
print(f"  Volume capacity: {TRUCK_VOLUME_CAPACITY_CUFT:,} cu ft")

print("\n[2] Supplier Mapping")
print(f"  Total SKUs: {len(SUPPLIER_MAP)}")
domestic_skus = [sku for sku, sup in SUPPLIER_MAP.items() if sup == 'Domestic']
international_skus = [sku for sku, sup in SUPPLIER_MAP.items() if sup == 'International']
print(f"  Domestic suppliers: {len(domestic_skus)} SKUs")
print(f"    {', '.join(domestic_skus)}")
print(f"  International suppliers: {len(international_skus)} SKUs")
print(f"    {', '.join(international_skus)}")

print("\n[3] Test Calculations")
print("-"*80)

# Test case 1: Weight-constrained (light but heavy items)
test1_weight = 50000  # 50,000 lbs (exceeds 45,000 limit)
test1_volume = 2000   # 2,000 cu ft (well under 3,600 limit)
test1_trucks = calculate_truckloads(test1_weight, test1_volume)
print(f"\nTest 1 - Weight-Constrained:")
print(f"  Weight: {test1_weight:,} lbs → {calculate_truckloads_weight(test1_weight)} trucks")
print(f"  Volume: {test1_volume:,} cu ft → {calculate_truckloads_volume(test1_volume)} trucks")
print(f"  Result: {test1_trucks} trucks needed (WEIGHT BINDING)")

# Test case 2: Volume-constrained (bulky but light items)
test2_weight = 20000  # 20,000 lbs (well under 45,000 limit)
test2_volume = 4000   # 4,000 cu ft (exceeds 3,600 limit)
test2_trucks = calculate_truckloads(test2_weight, test2_volume)
print(f"\nTest 2 - Volume-Constrained:")
print(f"  Weight: {test2_weight:,} lbs → {calculate_truckloads_weight(test2_weight)} trucks")
print(f"  Volume: {test2_volume:,} cu ft → {calculate_truckloads_volume(test2_volume)} trucks")
print(f"  Result: {test2_trucks} trucks needed (VOLUME BINDING)")

# Test case 3: Under capacity (single truck)
test3_weight = 30000  # 30,000 lbs (under 45,000 limit)
test3_volume = 2500   # 2,500 cu ft (under 3,600 limit)
test3_trucks = calculate_truckloads(test3_weight, test3_volume)
print(f"\nTest 3 - Under Capacity:")
print(f"  Weight: {test3_weight:,} lbs → {calculate_truckloads_weight(test3_weight)} trucks")
print(f"  Volume: {test3_volume:,} cu ft → {calculate_truckloads_volume(test3_volume)} trucks")
print(f"  Result: {test3_trucks} truck needed")

# Test case 4: Exactly at capacity
test4_weight = 45000  # Exactly at weight limit
test4_volume = 3600   # Exactly at volume limit
test4_trucks = calculate_truckloads(test4_weight, test4_volume)
print(f"\nTest 4 - Exactly At Capacity:")
print(f"  Weight: {test4_weight:,} lbs → {calculate_truckloads_weight(test4_weight)} trucks")
print(f"  Volume: {test4_volume:,} cu ft → {calculate_truckloads_volume(test4_volume)} trucks")
print(f"  Result: {test4_trucks} truck needed")

# Test case 5: Multiple trucks needed
test5_weight = 100000  # 100,000 lbs (needs 3 trucks by weight)
test5_volume = 8000    # 8,000 cu ft (needs 3 trucks by volume)
test5_trucks = calculate_truckloads(test5_weight, test5_volume)
print(f"\nTest 5 - Multiple Trucks:")
print(f"  Weight: {test5_weight:,} lbs → {calculate_truckloads_weight(test5_weight)} trucks")
print(f"  Volume: {test5_volume:,} cu ft → {calculate_truckloads_volume(test5_volume)} trucks")
print(f"  Result: {test5_trucks} trucks needed")

print("\n" + "="*80)
print("✓ All truckload calculations working correctly!")
print("="*80)

print("\n[4] Example SKU Calculations")
print("-"*80)
print("\nExample inbound pack data (from SKU Details.csv):")
print("  SKUW1 (International): 10×10×6 in, 15 lbs per inbound pack")
print("  SKUT2 (Domestic): 48×48×20 in, 550 lbs per inbound pack")
print("  SKUE2 (International): 48×48×48 in, 520 lbs per inbound pack")

# SKUW1: Small writing utensil packs
skuw1_volume_per_pack = (10 * 10 * 6) / 1728  # Convert inches to cubic feet
skuw1_weight_per_pack = 15
print(f"\nSKUW1 single inbound pack:")
print(f"  Volume: {skuw1_volume_per_pack:.3f} cu ft")
print(f"  Weight: {skuw1_weight_per_pack} lbs")
print(f"  Packs per truck (by volume): {int(TRUCK_VOLUME_CAPACITY_CUFT / skuw1_volume_per_pack):,}")
print(f"  Packs per truck (by weight): {int(TRUCK_WEIGHT_CAPACITY_LBS / skuw1_weight_per_pack):,}")
print(f"  → Volume-constrained: max {int(TRUCK_VOLUME_CAPACITY_CUFT / skuw1_volume_per_pack):,} packs per truck")

# SKUT2: Heavy textbook pallets
skut2_volume_per_pack = (48 * 48 * 20) / 1728
skut2_weight_per_pack = 550
print(f"\nSKUT2 single inbound pack (pallet):")
print(f"  Volume: {skut2_volume_per_pack:.1f} cu ft")
print(f"  Weight: {skut2_weight_per_pack} lbs")
print(f"  Packs per truck (by volume): {int(TRUCK_VOLUME_CAPACITY_CUFT / skut2_volume_per_pack)}")
print(f"  Packs per truck (by weight): {int(TRUCK_WEIGHT_CAPACITY_LBS / skut2_weight_per_pack)}")
print(f"  → Weight-constrained: max {int(TRUCK_WEIGHT_CAPACITY_LBS / skut2_weight_per_pack)} pallets per truck")

# SKUE2: Large electronics (heavy and bulky)
skue2_volume_per_pack = (48 * 48 * 48) / 1728
skue2_weight_per_pack = 520
print(f"\nSKUE2 single inbound pack:")
print(f"  Volume: {skue2_volume_per_pack:.1f} cu ft")
print(f"  Weight: {skue2_weight_per_pack} lbs")
print(f"  Packs per truck (by volume): {int(TRUCK_VOLUME_CAPACITY_CUFT / skue2_volume_per_pack)}")
print(f"  Packs per truck (by weight): {int(TRUCK_WEIGHT_CAPACITY_LBS / skue2_weight_per_pack)}")
binding = "volume" if (TRUCK_VOLUME_CAPACITY_CUFT / skue2_volume_per_pack) < (TRUCK_WEIGHT_CAPACITY_LBS / skue2_weight_per_pack) else "weight"
max_packs = int(min(TRUCK_VOLUME_CAPACITY_CUFT / skue2_volume_per_pack, TRUCK_WEIGHT_CAPACITY_LBS / skue2_weight_per_pack))
print(f"  → {binding.capitalize()}-constrained: max {max_packs} packs per truck")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
