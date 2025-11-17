"""
STOCHASTIC PHASE 2 MODEL - Monte Carlo Simulation with Exponential Delays
==========================================================================

Scenario: 4 days domestic DOH, 14 days international DOH

Stochastic Components:
- Number of delay events per month ~ Poisson(λ = k × base_lead_time)
- Duration of each delay event ~ Exponential(mean = μ days)

This script:
1. Runs deterministic baseline (4_14_doh)
2. Runs Monte Carlo simulations with various k and μ parameters
3. Compares stochastic results to baseline
4. Quantifies cost of uncertainty
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import subprocess
import json
import time
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DOH_DOMESTIC = 4
DOH_INTERNATIONAL = 14
SCENARIO_NAME = f"{DOH_INTERNATIONAL}_{DOH_DOMESTIC}_doh"

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / f"stochastic_{SCENARIO_NAME}"
STOCHASTIC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print(f"STOCHASTIC PHASE 2 MODEL - Monte Carlo Simulation")
print("="*100)
print(f"\nScenario: {SCENARIO_NAME}")
print(f"  - Domestic DOH: {DOH_DOMESTIC} days")
print(f"  - International DOH: {DOH_INTERNATIONAL} days")
print(f"\nStochastic Model:")
print(f"  - Delay events ~ Poisson(λ = k x base_lead_time)")
print(f"  - Delay duration ~ Exponential(mean = μ days)")
print()

# Load lead time data
def load_lead_times():
    """
    Load base lead times from template file.
    Calculates lead times based on DOH parameters.
    """
    # Load template file
    template_file = DATA_DIR / "Lead TIme.csv"

    if not template_file.exists():
        print(f"ERROR: Template file not found: {template_file}")
        sys.exit(1)

    df = pd.read_csv(template_file)

    lead_time_records = []

    for _, row in df.iterrows():
        sku = row['SKU Number']
        supplier_type = row['Supplier Type']

        # Select DOH based on supplier type from data
        is_international = (supplier_type == 'International')
        doh = DOH_INTERNATIONAL if is_international else DOH_DOMESTIC

        for facility in ['Columbus', 'Sacramento', 'Austin']:
            # Get base lead time from template
            lead_col = f'Lead Time - {facility}'
            if lead_col in df.columns:
                base_lead = float(row[lead_col])

                # Add DOH to get total lead time
                total_lead = base_lead + doh

                lead_time_records.append({
                    'SKU': sku,
                    'Facility': facility,
                    'Supplier_Type': 'International' if is_international else 'Domestic',
                    'Base_Lead_Time': base_lead,
                    'DOH': doh,
                    'Lead_Time_Days': total_lead
                })

    lead_df = pd.DataFrame(lead_time_records)

    print(f"\nLoaded {len(lead_df)} SKU-facility combinations")
    print(f"  Domestic SKUs: {len(lead_df[lead_df['Supplier_Type'] == 'Domestic'])} entries")
    print(f"  International SKUs: {len(lead_df[lead_df['Supplier_Type'] == 'International'])} entries")

    return lead_df

def generate_stochastic_lead_times(base_lead_times_df, k_factor, mean_delay, num_months=120):
    """
    Generate stochastic lead times using Poisson + Exponential.

    Args:
        base_lead_times_df: DataFrame with columns [SKU, Facility, Lead_Time_Days]
        k_factor: Proportionality constant for Poisson lambda (λ = k × lead_time)
        mean_delay: Mean delay duration in days (exponential parameter)
        num_months: Number of months in planning horizon

    Returns:
        DataFrame with stochastic lead times for each month
    """
    stochastic_records = []

    for _, row in base_lead_times_df.iterrows():
        sku = row['SKU']
        facility = row['Facility']
        base_lead = row['Lead_Time_Days']

        # Lambda proportional to base lead time
        lambda_val = k_factor * base_lead

        for month in range(1, num_months + 1):
            # Stage 1: Number of delay events ~ Poisson(λ)
            num_events = np.random.poisson(lambda_val)

            # Stage 2: Duration of each event ~ Exponential(mean)
            if num_events > 0:
                event_durations = np.random.exponential(mean_delay, size=num_events)
                total_delay_days = event_durations.sum()
            else:
                total_delay_days = 0

            # Total lead time for this month
            stochastic_lead = base_lead + total_delay_days

            stochastic_records.append({
                'Month': month,
                'SKU': sku,
                'Facility': facility,
                'Base_Lead_Time': base_lead,
                'Delay_Events': num_events,
                'Delay_Days': total_delay_days,
                'Total_Lead_Time': stochastic_lead
            })

    return pd.DataFrame(stochastic_records)

def create_modified_lead_time_file(stochastic_df, simulation_id):
    """
    Create modified lead time CSV file for this simulation.
    Uses average stochastic lead time across all months.
    """
    # Average lead time across all months for each SKU-facility pair
    avg_lead_times = stochastic_df.groupby(['SKU', 'Facility'])['Total_Lead_Time'].mean().reset_index()

    # Pivot to match original format
    lead_time_pivot = avg_lead_times.pivot(index='SKU', columns='Facility', values='Total_Lead_Time')
    lead_time_pivot.columns = [f'{col} Lead Time (business days)' for col in lead_time_pivot.columns]
    lead_time_pivot = lead_time_pivot.reset_index()

    # Save to temporary file
    temp_file = STOCHASTIC_RESULTS_DIR / f"temp_lead_time_sim_{simulation_id}.csv"
    lead_time_pivot.to_csv(temp_file, index=False)

    return temp_file

def run_deterministic_baseline():
    """Run deterministic baseline model."""
    print("\n" + "="*100)
    print("STEP 1: Running Deterministic Baseline")
    print("="*100)

    # Get script directory
    script_dir = Path(__file__).parent
    parameterized_script = script_dir / "phase2_DAILY_parameterized.py"

    cmd = [
        'python',
        str(parameterized_script),
        '--doh_intl', str(DOH_INTERNATIONAL),
        '--doh_dom', str(DOH_DOMESTIC),
        '--scenario_name', SCENARIO_NAME,
        '--max_time', '300'
    ]

    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR running baseline:")
        print(f"Return code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        print(f"\nSTDERR:\n{result.stderr}")
        return None

    # Print successful output
    print(result.stdout)

    # Load baseline results
    baseline_results_file = RESULTS_DIR / SCENARIO_NAME / f"expansion_requirements_{SCENARIO_NAME}.csv"

    if not baseline_results_file.exists():
        print(f"ERROR: Baseline results not found at {baseline_results_file}")
        return None

    baseline_df = pd.read_csv(baseline_results_file)

    baseline_summary = {
        'sacramento_shelves': baseline_df[baseline_df['Facility'] == 'Sacramento']['Expansion_Shelves'].iloc[0] if len(baseline_df[baseline_df['Facility'] == 'Sacramento']) > 0 else 0,
        'austin_shelves': baseline_df[baseline_df['Facility'] == 'Austin']['Expansion_Shelves'].iloc[0] if len(baseline_df[baseline_df['Facility'] == 'Austin']) > 0 else 0,
        'total_shelves': baseline_df[baseline_df['Facility'] == 'Total']['Expansion_Shelves'].iloc[0] if len(baseline_df[baseline_df['Facility'] == 'Total']) > 0 else 0
    }

    print(f"\nBaseline Results:")
    print(f"  Sacramento: {baseline_summary['sacramento_shelves']:,.0f} shelves")
    print(f"  Austin: {baseline_summary['austin_shelves']:,.0f} shelves")
    print(f"  Total: {baseline_summary['total_shelves']:,.0f} shelves")

    return baseline_summary

def run_monte_carlo_simulation(k_factor, mean_delay, num_simulations=50):
    """
    Run Monte Carlo simulation with specified k and mean_delay parameters.

    NOTE: Using 50 simulations for computational feasibility.
    Each simulation takes ~1-3 minutes.
    """
    print("\n" + "="*100)
    print(f"STEP 2: Running Monte Carlo Simulation")
    print(f"  k_factor = {k_factor} (Poisson rate)")
    print(f"  mean_delay = {mean_delay} days (Exponential mean)")
    print(f"  num_simulations = {num_simulations}")
    print("="*100)

    # Load base lead times
    base_lead_times = load_lead_times()

    results = []
    start_time = time.time()

    for sim in range(1, num_simulations + 1):
        sim_start = time.time()
        print(f"\n[Simulation {sim}/{num_simulations}] ", end='', flush=True)

        # Generate stochastic lead times
        stochastic_df = generate_stochastic_lead_times(
            base_lead_times,
            k_factor,
            mean_delay
        )

        # Save delay statistics for this simulation
        delay_stats = stochastic_df.groupby(['SKU', 'Facility']).agg({
            'Delay_Events': 'sum',
            'Delay_Days': 'sum',
            'Total_Lead_Time': 'mean'
        }).reset_index()

        delay_stats.to_csv(
            STOCHASTIC_RESULTS_DIR / f"delay_stats_sim_{sim}.csv",
            index=False
        )

        # For now, save the stochastic lead time summary and skip optimization
        # (Optimization integration can be added later)
        print(f"Generated delays - ", end='', flush=True)

        # Calculate summary stats
        avg_delay_per_sku = stochastic_df.groupby('SKU')['Delay_Days'].mean().mean()
        total_delay_events = stochastic_df['Delay_Events'].sum()

        results.append({
            'simulation': sim,
            'k_factor': k_factor,
            'mean_delay': mean_delay,
            'avg_delay_days': avg_delay_per_sku,
            'total_delay_events': total_delay_events,
            # Placeholder for optimization results
            'sacramento_shelves': np.nan,
            'austin_shelves': np.nan,
            'total_shelves': np.nan
        })

        elapsed = time.time() - sim_start
        print(f"completed in {elapsed:.1f}s")

    total_time = time.time() - start_time
    print(f"\nMonte Carlo completed in {total_time/60:.1f} minutes")

    return pd.DataFrame(results)

def analyze_results(baseline, mc_results_df, k_factor, mean_delay):
    """Analyze and compare stochastic results to baseline."""
    print("\n" + "="*100)
    print("STEP 3: Results Analysis")
    print("="*100)

    print(f"\nStochastic Model Parameters:")
    print(f"  k_factor = {k_factor}")
    print(f"  mean_delay = {mean_delay} days")
    print(f"  Number of simulations = {len(mc_results_df)}")

    print(f"\nDelay Statistics:")
    print(f"  Avg delay per SKU: {mc_results_df['avg_delay_days'].mean():.2f} days")
    print(f"  Total delay events (all sims): {mc_results_df['total_delay_events'].sum():.0f}")

    # NOTE: Optimization integration placeholder
    print(f"\nNOTE: Full optimization integration pending.")
    print(f"      Current output shows delay generation only.")

    # Save summary
    summary_df = pd.DataFrame([{
        'Scenario': f"{DOH_INTERNATIONAL}_{DOH_DOMESTIC}_doh",
        'k_factor': k_factor,
        'mean_delay': mean_delay,
        'num_simulations': len(mc_results_df),
        'baseline_total_shelves': baseline['total_shelves'] if baseline else np.nan,
        'avg_delay_days': mc_results_df['avg_delay_days'].mean(),
        'total_delay_events': mc_results_df['total_delay_events'].sum(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }])

    summary_file = STOCHASTIC_RESULTS_DIR / f"stochastic_summary_k{k_factor}_mu{mean_delay}.csv"
    summary_df.to_csv(summary_file, index=False)

    # Save detailed results
    mc_results_df.to_csv(
        STOCHASTIC_RESULTS_DIR / f"mc_results_k{k_factor}_mu{mean_delay}.csv",
        index=False
    )

    print(f"\nResults saved to: {STOCHASTIC_RESULTS_DIR}")

def main():
    """Main execution."""

    # Step 1: Run deterministic baseline
    baseline = run_deterministic_baseline()

    if baseline is None:
        print("\nERROR: Could not run baseline. Check lead time files.")
        print(f"Expected file: Model Data/Lead TIme_{DOH_INTERNATIONAL}_{DOH_DOMESTIC}_business_days.csv")
        return

    # Step 2: Define stochastic scenarios
    scenarios = [
        # (k_factor, mean_delay, description)
        (0.05, 2.0, 'Low Risk'),
        (0.10, 5.0, 'Medium Risk'),
        (0.15, 10.0, 'High Risk'),
    ]

    print("\n" + "="*100)
    print("Stochastic Scenarios:")
    for k, mu, desc in scenarios:
        print(f"  {desc}: k={k}, μ={mu} days")
    print("="*100)

    # Step 3: Run Monte Carlo for each scenario
    for k_factor, mean_delay, description in scenarios:
        print(f"\n\n{'#'*100}")
        print(f"SCENARIO: {description}")
        print(f"{'#'*100}")

        mc_results = run_monte_carlo_simulation(
            k_factor,
            mean_delay,
            num_simulations=50  # Reduced for computational feasibility
        )

        analyze_results(baseline, mc_results, k_factor, mean_delay)

    print("\n" + "="*100)
    print("STOCHASTIC ANALYSIS COMPLETE")
    print("="*100)
    print(f"\nResults directory: {STOCHASTIC_RESULTS_DIR}")
    print("\nGenerated files:")
    print("  - stochastic_summary_k*_mu*.csv : Summary statistics")
    print("  - mc_results_k*_mu*.csv : Detailed Monte Carlo results")
    print("  - delay_stats_sim_*.csv : Delay statistics per simulation")

if __name__ == "__main__":
    main()
