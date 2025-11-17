"""
TRUCKLOAD CONSTANTS
===================

Standard 53-foot trailer specifications for supplier delivery tracking.

Usage: Import these constants into phase2 models to calculate trucks per day per supplier.
"""

import pandas as pd
from pathlib import Path

# 53-foot trailer standard capacity
TRUCK_WEIGHT_CAPACITY_LBS = 45000  # pounds
TRUCK_VOLUME_CAPACITY_CUFT = 3600  # cubic feet

# Truck dispatch optimization parameters
TRUCK_COST_PER_DELIVERY = 100  # Cost per truck delivery (set low to minimize trucks without dominating objective)
MIN_TRUCK_UTILIZATION = 0.90  # Minimum 90% utilization on binding constraint before dispatch

# Load supplier information from CSV
def load_supplier_info():
    """Load supplier information from supplierinformation.csv"""
    # Try model2.0 structure first
    data_dir = Path(__file__).parent / "Model Data"
    supplier_file = data_dir / "supplierinformation.csv"

    # If not found, try parent directory structure
    if not supplier_file.exists():
        data_dir = Path(__file__).parent.parent / "Model Data"
        supplier_file = data_dir / "supplierinformation.csv"

    if not supplier_file.exists():
        raise FileNotFoundError(f"Could not find supplierinformation.csv. Searched: {supplier_file}")

    supplier_df = pd.read_csv(supplier_file)

    # Create SKU to supplier name mapping
    sku_to_supplier = {}
    sku_to_supplier_type = {}

    for _, row in supplier_df.iterrows():
        sku = row['SKU Number']
        supplier_name = row['Supplier']
        supplier_type = row['Supplier Type']

        sku_to_supplier[sku] = supplier_name
        sku_to_supplier_type[sku] = supplier_type

    # Get unique suppliers
    unique_suppliers = supplier_df['Supplier'].unique().tolist()

    return sku_to_supplier, sku_to_supplier_type, unique_suppliers

# Load supplier data
SKU_TO_SUPPLIER, SKU_TO_SUPPLIER_TYPE, SUPPLIERS = load_supplier_info()

# Legacy mapping for backward compatibility
SUPPLIER_MAP = SKU_TO_SUPPLIER_TYPE  # Maps SKU to 'Domestic' or 'International'
SUPPLIER_TYPES = ['Domestic', 'International']

def calculate_truckloads_weight(total_weight_lbs):
    """
    Calculate number of trucks needed based on weight constraint.

    Args:
        total_weight_lbs: Total weight in pounds

    Returns:
        Number of trucks needed (rounded up)
    """
    import math
    return math.ceil(total_weight_lbs / TRUCK_WEIGHT_CAPACITY_LBS)

def calculate_truckloads_volume(total_volume_cuft):
    """
    Calculate number of trucks needed based on volume constraint.

    Args:
        total_volume_cuft: Total volume in cubic feet

    Returns:
        Number of trucks needed (rounded up)
    """
    import math
    return math.ceil(total_volume_cuft / TRUCK_VOLUME_CAPACITY_CUFT)

def calculate_truckloads(total_weight_lbs, total_volume_cuft):
    """
    Calculate number of trucks needed based on BOTH weight and volume constraints.
    Returns the maximum of the two constraints (binding constraint).

    Args:
        total_weight_lbs: Total weight in pounds
        total_volume_cuft: Total volume in cubic feet

    Returns:
        Number of trucks needed (max of weight-based and volume-based)
    """
    trucks_by_weight = calculate_truckloads_weight(total_weight_lbs)
    trucks_by_volume = calculate_truckloads_volume(total_volume_cuft)
    return max(trucks_by_weight, trucks_by_volume)

def calculate_truck_utilization(total_weight_lbs, total_volume_cuft, num_trucks):
    """
    Calculate truck utilization percentages for weight and volume.

    Args:
        total_weight_lbs: Total weight in pounds
        total_volume_cuft: Total volume in cubic feet
        num_trucks: Number of trucks used

    Returns:
        dict with keys:
            - weight_utilization_pct: % of weight capacity used
            - volume_utilization_pct: % of volume capacity used
            - binding_constraint: 'weight' or 'volume' (which constraint limits capacity)
            - avg_weight_per_truck: Average weight per truck
            - avg_volume_per_truck: Average volume per truck
    """
    if num_trucks == 0:
        return {
            'weight_utilization_pct': 0.0,
            'volume_utilization_pct': 0.0,
            'binding_constraint': None,
            'avg_weight_per_truck': 0.0,
            'avg_volume_per_truck': 0.0
        }

    total_weight_capacity = num_trucks * TRUCK_WEIGHT_CAPACITY_LBS
    total_volume_capacity = num_trucks * TRUCK_VOLUME_CAPACITY_CUFT

    weight_util_pct = (total_weight_lbs / total_weight_capacity * 100) if total_weight_capacity > 0 else 0
    volume_util_pct = (total_volume_cuft / total_volume_capacity * 100) if total_volume_capacity > 0 else 0

    # Determine binding constraint (which one forced us to use this many trucks)
    binding = 'weight' if weight_util_pct >= volume_util_pct else 'volume'

    return {
        'weight_utilization_pct': weight_util_pct,
        'volume_utilization_pct': volume_util_pct,
        'binding_constraint': binding,
        'avg_weight_per_truck': total_weight_lbs / num_trucks,
        'avg_volume_per_truck': total_volume_cuft / num_trucks
    }
