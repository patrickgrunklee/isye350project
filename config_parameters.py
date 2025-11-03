"""
CONFIGURATION PARAMETERS - Easily adjustable model parameters
=============================================================

Change these parameters to test different scenarios.
To revert changes, simply change the values back to defaults.

DEFAULT VALUES (from original Shelving Count.csv):
- Pallet weight capacity: 600 lbs
- Bins weight capacity: 30 lbs (Austin/Sacramento), 66.14 lbs (Columbus)
- Racking weight capacity: 100 lbs
- Hazmat weight capacity: 100 lbs

CURRENT SCENARIO: 4,000 LBS PALLET CAPACITY TEST
"""

# Weight capacities by storage type (lbs per shelf)
WEIGHT_CAPACITY = {
    'Pallet': 4000.0,      # MODIFIED: Changed from 600 to 4,000 lbs
    'Bins': 30.0,          # Default for Austin/Sacramento
    'Bins_Columbus': 66.14,  # Special case for Columbus
    'Racking': 100.0,      # Default
    'Hazmat': 100.0        # Default
}

# Package capacity by storage type (max items per shelf)
PACKAGE_CAPACITY = {
    # Austin
    ('Austin', 'Pallet'): 6,
    ('Austin', 'Bins'): 3,
    ('Austin', 'Racking'): 8,
    ('Austin', 'Hazmat'): 999999,  # No practical limit

    # Columbus
    ('Columbus', 'Pallet'): 7,
    ('Columbus', 'Bins'): 6,
    ('Columbus', 'Racking'): 8,
    ('Columbus', 'Hazmat'): 999999,

    # Sacramento
    ('Sacramento', 'Pallet'): 4,
    ('Sacramento', 'Bins'): 3,
    ('Sacramento', 'Racking'): 8,
    ('Sacramento', 'Hazmat'): 999999
}

# Storage type volume constraints (max item volume per package in cu ft)
MAX_ITEM_VOLUME = {
    'Bins': 1.0,       # 12×12×12 inches
    'Racking': 1.953,  # 15×15×15 inches
    'Pallet': 64.0,    # 48×48×48 inches
    'Hazmat': 1.953    # 15×15×15 inches
}

# Shelf volume capacity by (facility, storage_type) in cubic feet
SHELF_VOLUME = {
    ('Columbus', 'Pallet'): 1020.0,    # 10×4.25×24 ft
    ('Columbus', 'Racking'): 27.0,     # 3×1.5×6 ft
    ('Columbus', 'Bins'): 3.47,        # 1.975×1.325×1.325 ft (23.7×15.9×15.9 in)

    ('Austin', 'Pallet'): 765.0,       # 10×4.25×18 ft
    ('Austin', 'Racking'): 27.0,       # 3×1.5×6 ft
    ('Austin', 'Bins'): 6.25,          # 1.25×1.25×4 ft

    ('Sacramento', 'Pallet'): 510.0,   # 5×4.25×24 ft
    ('Sacramento', 'Racking'): 27.0,   # 3×1.5×6 ft
    ('Sacramento', 'Bins'): 6.25       # 1.25×1.25×4 ft
}

def get_weight_capacity(facility, storage_type):
    """Get weight capacity for a specific facility and storage type"""
    if storage_type == 'Bins' and facility == 'Columbus':
        return WEIGHT_CAPACITY['Bins_Columbus']
    else:
        return WEIGHT_CAPACITY.get(storage_type, 100.0)

def get_package_capacity(facility, storage_type):
    """Get max package capacity for a specific facility and storage type"""
    return PACKAGE_CAPACITY.get((facility, storage_type), 999999)

def get_max_item_volume(storage_type):
    """Get max item volume constraint for a storage type"""
    return MAX_ITEM_VOLUME.get(storage_type, 999.0)

def get_shelf_volume(facility, storage_type):
    """Get shelf volume for a specific facility and storage type"""
    return SHELF_VOLUME.get((facility, storage_type), 100.0)

# Print current configuration
if __name__ == "__main__":
    print("="*100)
    print("CURRENT CONFIGURATION PARAMETERS")
    print("="*100)

    print("\n[WEIGHT CAPACITIES - MODIFIED]")
    print(f"  Pallet:              {WEIGHT_CAPACITY['Pallet']:>8,.0f} lbs  *** CHANGED FROM 600 TO 4,000 ***")
    print(f"  Bins (Austin/Sac):   {WEIGHT_CAPACITY['Bins']:>8,.2f} lbs")
    print(f"  Bins (Columbus):     {WEIGHT_CAPACITY['Bins_Columbus']:>8,.2f} lbs")
    print(f"  Racking:             {WEIGHT_CAPACITY['Racking']:>8,.0f} lbs")
    print(f"  Hazmat:              {WEIGHT_CAPACITY['Hazmat']:>8,.0f} lbs")

    print("\n[MAX ITEM VOLUMES]")
    for st, vol in MAX_ITEM_VOLUME.items():
        print(f"  {st:<12}     {vol:>8.3f} cu ft")

    print("\n[PACKAGE CAPACITIES]")
    for (fac, st), cap in sorted(PACKAGE_CAPACITY.items()):
        if cap < 999:
            print(f"  {fac:<12} {st:<10}  {cap:>5} packages/shelf")

    print("\n" + "="*100)
    print("To revert changes: Edit config_parameters.py and change WEIGHT_CAPACITY['Pallet'] back to 600.0")
    print("="*100)
