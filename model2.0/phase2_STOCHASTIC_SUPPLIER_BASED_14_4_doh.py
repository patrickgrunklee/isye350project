"""
STOCHASTIC PHASE 2 MODEL - Supplier-Based Monte Carlo Simulation
==================================================================

Scenario: 4 days domestic DOH, 14 days international DOH

REVISED APPROACH - Supplier-Level Delays:
- Delays occur at SUPPLIER-FACILITY-DAY level (not individual SKUs)
- When a supplier's truckload is delayed, ALL SKUs on that delivery are delayed together
- This creates realistic compounding effects where multiple SKUs face correlated delays

Stochastic Components:
- Number of delay events per supplier-month ~ Poisson(λ = k × avg_lead_time)
- Duration of each delay event ~ Exponential(mean = μ days)
- Delays apply to entire truckload (all SKUs from that supplier)

This script:
1. Loads/generates truckload delivery schedule for 14_4_doh scenario
2. Runs deterministic baseline
3. Runs Monte Carlo simulations with supplier-level delays
4. Analyzes impact of correlated delays on inventory requirements
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
import time
from datetime import datetime
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DOH_DOMESTIC = 4
DOH_INTERNATIONAL = 14
SCENARIO_NAME = f"{DOH_INTERNATIONAL}_{DOH_DOMESTIC}_doh"

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / f"stochastic_supplier_{SCENARIO_NAME}"
STOCHASTIC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print(f"STOCHASTIC PHASE 2 MODEL - Supplier-Based Monte Carlo Simulation")
print("="*100)
print(f"\nScenario: {SCENARIO_NAME}")
print(f"  - Domestic DOH: {DOH_DOMESTIC} days")
print(f"  - International DOH: {DOH_INTERNATIONAL} days")
print(f"\nREVISED Stochastic Model (Supplier-Level Delays):")
print(f"  - Delays occur at SUPPLIER-FACILITY-DAY level")
print(f"  - When supplier is delayed, ALL SKUs on that truck are delayed together")
print(f"  - Delay events ~ Poisson(λ = k x deliveries_per_month)")
print(f"  - Delay duration ~ Exponential(mean = μ days)")
print()

# Supplier mapping (from SKU Details)
SUPPLIER_MAPPING = {
    'The Write Stuff': {
        'type': 'International',
        'skus': ['SKUW1', 'SKUW2', 'SKUW3']
    },
    'Canvas & Co.': {
        'type': 'Domestic',
        'skus': ['SKUA1', 'SKUA2', 'SKUA3']
    },
    'Bound to Learn': {
        'type': 'Domestic',
        'skus': ['SKUT1', 'SKUT2', 'SKUT3', 'SKUT4']
    },
    'Form & Function': {
        'type': 'Domestic',
        'skus': ['SKUD1', 'SKUD2', 'SKUD3', 'SKUC1', 'SKUC2']
    },
    'VoltEdge': {
        'type': 'International',
        'skus': ['SKUE1', 'SKUE2', 'SKUE3']
    }
}

# Reverse mapping: SKU -> Supplier
SKU_TO_SUPPLIER = {}
for supplier, info in SUPPLIER_MAPPING.items():
    for sku in info['skus']:
        SKU_TO_SUPPLIER[sku] = supplier

def load_or_generate_truckload_schedule():
    """
    Load truckload schedule for 14_4_doh scenario.
    If not available, generate a representative schedule based on 3_1_doh pattern.
    """
    # Check if truckload analysis exists for this scenario
    truckload_file = RESULTS_DIR / SCENARIO_NAME / f"truckload_analysis_{SCENARIO_NAME}.csv"

    if truckload_file.exists():
        print(f"\nLoading existing truckload schedule: {truckload_file}")
        df = pd.read_csv(truckload_file)
        return df

    # Use 3_1_doh as template pattern
    template_file = RESULTS_DIR / "truckload_analysis_3_1_doh.csv"

    if not template_file.exists():
        print(f"ERROR: Template truckload file not found: {template_file}")
        print(f"Please run phase2_DAILY_3_1_doh.py first to generate template.")
        sys.exit(1)

    print(f"\nGenerating truckload schedule from template: {template_file}")
    template_df = pd.read_csv(template_file)

    # For now, use the template pattern as-is
    # (In production, would regenerate based on actual 14_4_doh demand)
    print(f"  Using 3_1_doh pattern as approximation")
    print(f"  Loaded {len(template_df)} truckload deliveries")

    return template_df

def generate_supplier_delays(truckload_schedule, k_factor, mean_delay, num_months=120):
    """
    Generate stochastic delays at SUPPLIER-FACILITY-DAY level.

    Key difference from SKU-level model:
    - Delays are generated for each (supplier, facility, month, day) delivery
    - When a supplier is delayed, ALL SKUs on that delivery are affected
    - ALL TRUCKS in that delivery are delayed together
    - This creates correlated delays within supplier shipments

    Args:
        truckload_schedule: DataFrame with columns [Month, Day, Facility, Supplier, SKUs_Delivered, Trucks_Needed]
        k_factor: Proportionality constant for Poisson lambda
        mean_delay: Mean delay duration in days (exponential parameter)
        num_months: Number of months in planning horizon

    Returns:
        DataFrame with delay records at supplier-day level including truck counts
    """
    delay_records = []

    # Group deliveries by (Supplier, Facility) to calculate delivery frequency
    supplier_facility_groups = truckload_schedule.groupby(['Supplier', 'Facility', 'Supplier_Type'])

    for (supplier, facility, supplier_type), group in supplier_facility_groups:
        # Calculate average deliveries per month for this supplier-facility pair
        deliveries_per_month = len(group) / num_months

        # Lambda proportional to delivery frequency
        # More frequent deliveries = more opportunities for delays
        lambda_val = k_factor * deliveries_per_month

        # Generate delays for each month
        for month in range(1, num_months + 1):
            # Get actual deliveries this month
            month_deliveries = group[group['Month'] == month]

            # Stage 1: Number of delay events this month ~ Poisson(λ)
            num_events = np.random.poisson(lambda_val)

            # Stage 2: Duration of each event ~ Exponential(mean)
            if num_events > 0 and len(month_deliveries) > 0:
                for event_idx in range(num_events):
                    delay_duration = np.random.exponential(mean_delay)

                    # Randomly select which delivery day is affected
                    affected_delivery = month_deliveries.sample(n=1).iloc[0]
                    day = affected_delivery['Day']
                    skus_delivered = affected_delivery['SKUs_Delivered']
                    trucks_needed = affected_delivery['Trucks_Needed']

                    # Parse SKUs (comma-separated string)
                    if isinstance(skus_delivered, str):
                        sku_list = [s.strip() for s in skus_delivered.split(',')]
                    else:
                        sku_list = []

                    # Calculate truck-days of delay (trucks × delay_days)
                    truck_days_delay = trucks_needed * delay_duration

                    delay_records.append({
                        'Month': month,
                        'Day': day,
                        'Facility': facility,
                        'Supplier': supplier,
                        'Supplier_Type': supplier_type,
                        'Delay_Duration_Days': delay_duration,
                        'Trucks_Affected': trucks_needed,
                        'Truck_Days_Delay': truck_days_delay,
                        'Num_SKUs_Affected': len(sku_list),
                        'SKUs_Affected': skus_delivered,
                        'Event_Index': event_idx
                    })

    return pd.DataFrame(delay_records)

def run_monte_carlo_simulation(truckload_schedule, k_factor, mean_delay, num_simulations=50):
    """
    Run Monte Carlo simulation with supplier-level delays.
    """
    print("\n" + "="*100)
    print(f"STEP 2: Running Monte Carlo Simulation (Supplier-Level Delays)")
    print(f"  k_factor = {k_factor} (Poisson rate per delivery frequency)")
    print(f"  mean_delay = {mean_delay} days (Exponential mean)")
    print(f"  num_simulations = {num_simulations}")
    print("="*100)

    num_months = truckload_schedule['Month'].max()
    print(f"\nTruckload schedule: {num_months} months, {len(truckload_schedule)} total deliveries")

    # Analyze delivery pattern
    supplier_stats = truckload_schedule.groupby(['Supplier', 'Supplier_Type']).size().reset_index(name='Total_Deliveries')
    supplier_stats['Deliveries_Per_Month'] = supplier_stats['Total_Deliveries'] / num_months
    print(f"\nSupplier delivery frequencies:")
    print(supplier_stats.to_string(index=False))

    results = []
    start_time = time.time()

    for sim in range(1, num_simulations + 1):
        sim_start = time.time()
        print(f"\n[Simulation {sim}/{num_simulations}] ", end='', flush=True)

        # Generate supplier-level delays
        delay_df = generate_supplier_delays(
            truckload_schedule,
            k_factor,
            mean_delay,
            num_months=num_months
        )

        # Save detailed delay records with scenario-specific naming
        delay_df.to_csv(
            STOCHASTIC_RESULTS_DIR / f"supplier_delays_k{k_factor}_mu{mean_delay}_sim_{sim}.csv",
            index=False
        )

        # Calculate summary statistics
        total_delay_events = len(delay_df)
        total_skus_affected = delay_df['Num_SKUs_Affected'].sum()
        total_trucks_affected = delay_df['Trucks_Affected'].sum() if 'Trucks_Affected' in delay_df.columns else 0
        total_truck_days_delay = delay_df['Truck_Days_Delay'].sum() if 'Truck_Days_Delay' in delay_df.columns else 0
        avg_delay_duration = delay_df['Delay_Duration_Days'].mean() if len(delay_df) > 0 else 0
        avg_skus_per_event = delay_df['Num_SKUs_Affected'].mean() if len(delay_df) > 0 else 0
        avg_trucks_per_event = delay_df['Trucks_Affected'].mean() if len(delay_df) > 0 and 'Trucks_Affected' in delay_df.columns else 0

        # Count by supplier type
        domestic_events = len(delay_df[delay_df['Supplier_Type'] == 'Domestic'])
        international_events = len(delay_df[delay_df['Supplier_Type'] == 'International'])

        results.append({
            'simulation': sim,
            'k_factor': k_factor,
            'mean_delay': mean_delay,
            'total_delay_events': total_delay_events,
            'total_skus_affected': total_skus_affected,
            'total_trucks_affected': total_trucks_affected,
            'total_truck_days_delay': total_truck_days_delay,
            'avg_delay_duration': avg_delay_duration,
            'avg_skus_per_event': avg_skus_per_event,
            'avg_trucks_per_event': avg_trucks_per_event,
            'domestic_events': domestic_events,
            'international_events': international_events,
            # Placeholder for optimization results
            'sacramento_shelves': np.nan,
            'austin_shelves': np.nan,
            'total_shelves': np.nan
        })

        elapsed = time.time() - sim_start
        print(f"{total_delay_events} events, {total_trucks_affected:.0f} trucks, {total_truck_days_delay:.0f} truck-days - {elapsed:.1f}s")

    total_time = time.time() - start_time
    print(f"\nMonte Carlo completed in {total_time/60:.1f} minutes")

    return pd.DataFrame(results)

def analyze_results(mc_results_df, k_factor, mean_delay):
    """Analyze and summarize supplier-level delay results."""
    print("\n" + "="*100)
    print("STEP 3: Results Analysis (Supplier-Level Delays)")
    print("="*100)

    print(f"\nStochastic Model Parameters:")
    print(f"  k_factor = {k_factor}")
    print(f"  mean_delay = {mean_delay} days")
    print(f"  Number of simulations = {len(mc_results_df)}")

    print(f"\nDelay Statistics (averages across simulations):")
    print(f"  Total delay events: {mc_results_df['total_delay_events'].mean():.1f} ± {mc_results_df['total_delay_events'].std():.1f}")
    print(f"  Total SKU impacts: {mc_results_df['total_skus_affected'].mean():.1f} ± {mc_results_df['total_skus_affected'].std():.1f}")
    print(f"  Total trucks affected: {mc_results_df['total_trucks_affected'].mean():.0f} ± {mc_results_df['total_trucks_affected'].std():.0f}")
    print(f"  Total truck-days delay: {mc_results_df['total_truck_days_delay'].mean():.0f} ± {mc_results_df['total_truck_days_delay'].std():.0f}")
    print(f"  Avg delay duration: {mc_results_df['avg_delay_duration'].mean():.2f} days")
    print(f"  Avg SKUs per event: {mc_results_df['avg_skus_per_event'].mean():.2f}")
    print(f"  Avg trucks per event: {mc_results_df['avg_trucks_per_event'].mean():.1f}")
    print(f"  Domestic events: {mc_results_df['domestic_events'].mean():.1f}")
    print(f"  International events: {mc_results_df['international_events'].mean():.1f}")

    # Calculate multiplication effect
    avg_events = mc_results_df['total_delay_events'].mean()
    avg_sku_impacts = mc_results_df['total_skus_affected'].mean()
    avg_truck_impacts = mc_results_df['total_trucks_affected'].mean()
    sku_multiplication = avg_sku_impacts / avg_events if avg_events > 0 else 0
    truck_multiplication = avg_truck_impacts / avg_events if avg_events > 0 else 0

    print(f"\nMultiplication Effect (Compounding):")
    print(f"  Each supplier delay event affects {sku_multiplication:.2f} SKUs on average")
    print(f"  Each supplier delay event affects {truck_multiplication:.1f} trucks on average")
    print(f"  (Because each truckload contains multiple SKUs and trucks)")

    # Save summary
    summary_df = pd.DataFrame([{
        'Scenario': f"{DOH_INTERNATIONAL}_{DOH_DOMESTIC}_doh",
        'k_factor': k_factor,
        'mean_delay': mean_delay,
        'num_simulations': len(mc_results_df),
        'avg_delay_events': mc_results_df['total_delay_events'].mean(),
        'avg_sku_impacts': mc_results_df['total_skus_affected'].mean(),
        'avg_truck_impacts': mc_results_df['total_trucks_affected'].mean(),
        'avg_truck_days_delay': mc_results_df['total_truck_days_delay'].mean(),
        'sku_multiplication': sku_multiplication,
        'truck_multiplication': truck_multiplication,
        'avg_delay_duration': mc_results_df['avg_delay_duration'].mean(),
        'domestic_events': mc_results_df['domestic_events'].mean(),
        'international_events': mc_results_df['international_events'].mean(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }])

    summary_file = STOCHASTIC_RESULTS_DIR / f"supplier_summary_k{k_factor}_mu{mean_delay}.csv"
    summary_df.to_csv(summary_file, index=False)

    # Save detailed results
    mc_results_df.to_csv(
        STOCHASTIC_RESULTS_DIR / f"supplier_mc_results_k{k_factor}_mu{mean_delay}.csv",
        index=False
    )

    print(f"\nResults saved to: {STOCHASTIC_RESULTS_DIR}")

def main():
    """Main execution."""

    # Step 1: Load or generate truckload schedule
    truckload_schedule = load_or_generate_truckload_schedule()

    # Step 2: Define stochastic scenarios
    # REVISED: User-specified parameter combinations
    scenarios = [
        # (k_factor, mean_delay, description)
        (0.1, 3.0, 'Low Disruption'),
        (0.3, 5.0, 'Moderate Disruption'),
        (0.5, 14.0, 'High Disruption'),
    ]

    print("\n" + "="*100)
    print("Stochastic Scenarios (Supplier-Level):")
    for k, mu, desc in scenarios:
        print(f"  {desc}: k={k}, μ={mu} days")
    print("="*100)

    # Step 3: Run Monte Carlo for each scenario
    for k_factor, mean_delay, description in scenarios:
        print(f"\n\n{'#'*100}")
        print(f"SCENARIO: {description}")
        print(f"{'#'*100}")

        mc_results = run_monte_carlo_simulation(
            truckload_schedule,
            k_factor,
            mean_delay,
            num_simulations=50
        )

        analyze_results(mc_results, k_factor, mean_delay)

    print("\n" + "="*100)
    print("SUPPLIER-LEVEL STOCHASTIC ANALYSIS COMPLETE")
    print("="*100)
    print(f"\nResults directory: {STOCHASTIC_RESULTS_DIR}")
    print("\nGenerated files:")
    print("  - supplier_summary_k*_mu*.csv : Summary statistics")
    print("  - supplier_mc_results_k*_mu*.csv : Detailed Monte Carlo results")
    print("  - supplier_delays_sim_*.csv : Delay records per simulation")

if __name__ == "__main__":
    main()
