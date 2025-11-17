"""
STOCHASTIC STORAGE IMPACT ESTIMATION
=====================================

Estimates storage requirements under stochastic delays using linear scaling.

Logic:
- Inventory requirements scale linearly with DOH (safety stock)
- Storage space scales linearly with average inventory
- Therefore: Shelves_needed ≈ Shelves_baseline × (New_DOH / Base_DOH)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
DOH_DOMESTIC_BASE = 4
DOH_INTERNATIONAL_BASE = 14
BASELINE_SHELVES = 3994  # From 14_4_doh baseline run

RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / f"stochastic_supplier_14_4_doh"

print("="*100)
print("STOCHASTIC STORAGE IMPACT ESTIMATION")
print("="*100)
print(f"\nBaseline:")
print(f"  Domestic DOH: {DOH_DOMESTIC_BASE} days")
print(f"  International DOH: {DOH_INTERNATIONAL_BASE} days")
print(f"  Total shelves needed: {BASELINE_SHELVES:,}")
print()

def load_stochastic_summary(k_factor, mean_delay):
    """Load summary results from stochastic simulation."""
    summary_file = STOCHASTIC_RESULTS_DIR / f"supplier_summary_k{k_factor}_mu{mean_delay}.csv"

    if not summary_file.exists():
        print(f"WARNING: Summary file not found: {summary_file}")
        return None

    df = pd.read_csv(summary_file)
    return df.iloc[0]

def estimate_storage_impact(summary, description):
    """
    Estimate storage requirements using linear scaling.

    Assumptions:
    - 2/3 of inventory is domestic (shorter lead times, higher turnover)
    - 1/3 of inventory is international (longer lead times)
    - Storage scales linearly with DOH
    """

    # Calculate average delay per delivery
    avg_truck_days = summary['avg_truck_days_delay']
    avg_trucks = summary['avg_truck_impacts']
    avg_delay_per_delivery = avg_truck_days / avg_trucks if avg_trucks > 0 else 0

    # Effective DOH needed
    effective_doh_domestic = DOH_DOMESTIC_BASE + avg_delay_per_delivery
    effective_doh_international = DOH_INTERNATIONAL_BASE + avg_delay_per_delivery

    # Estimate inventory split (approximation based on SKU counts)
    # 12 domestic SKUs, 6 international SKUs
    domestic_inventory_fraction = 12 / 18
    international_inventory_fraction = 6 / 18

    # Calculate weighted DOH increase
    domestic_doh_multiplier = effective_doh_domestic / DOH_DOMESTIC_BASE
    international_doh_multiplier = effective_doh_international / DOH_INTERNATIONAL_BASE

    # Weighted average multiplier
    avg_multiplier = (domestic_inventory_fraction * domestic_doh_multiplier +
                      international_inventory_fraction * international_doh_multiplier)

    # Estimate new storage requirements
    estimated_shelves = BASELINE_SHELVES * avg_multiplier
    additional_shelves = estimated_shelves - BASELINE_SHELVES
    percent_increase = ((estimated_shelves / BASELINE_SHELVES) - 1) * 100

    return {
        'scenario': description,
        'k_factor': summary['k_factor'],
        'mean_delay': summary['mean_delay'],
        'avg_delay_per_delivery': avg_delay_per_delivery,
        'effective_doh_domestic': effective_doh_domestic,
        'effective_doh_international': effective_doh_international,
        'doh_multiplier_domestic': domestic_doh_multiplier,
        'doh_multiplier_international': international_doh_multiplier,
        'avg_multiplier': avg_multiplier,
        'baseline_shelves': BASELINE_SHELVES,
        'estimated_shelves': estimated_shelves,
        'additional_shelves': additional_shelves,
        'percent_increase': percent_increase
    }

def main():
    """Main execution."""

    scenarios = [
        (0.1, 3.0, 'Low Disruption'),
        (0.3, 5.0, 'Moderate Disruption'),
        (0.5, 14.0, 'High Disruption'),
    ]

    results = []

    for k, mu, desc in scenarios:
        print(f"\n{'#'*100}")
        print(f"SCENARIO: {desc}")
        print(f"  k={k}, mu={mu} days")
        print("#"*100)

        summary = load_stochastic_summary(k, mu)

        if summary is None:
            print(f"ERROR: Could not load stochastic results")
            continue

        impact = estimate_storage_impact(summary, desc)
        results.append(impact)

        print(f"\nStochastic Delay Impact:")
        print(f"  Average delay per delivery: {impact['avg_delay_per_delivery']:.2f} days")
        print(f"\nEffective DOH Requirements:")
        print(f"  Domestic: {DOH_DOMESTIC_BASE} -> {impact['effective_doh_domestic']:.1f} days ({impact['doh_multiplier_domestic']:.2f}x increase)")
        print(f"  International: {DOH_INTERNATIONAL_BASE} -> {impact['effective_doh_international']:.1f} days ({impact['doh_multiplier_international']:.2f}x increase)")
        print(f"  Weighted average multiplier: {impact['avg_multiplier']:.2f}x")
        print(f"\nEstimated Storage Requirements:")
        print(f"  Baseline: {impact['baseline_shelves']:,.0f} shelves")
        print(f"  With delays: {impact['estimated_shelves']:,.0f} shelves")
        print(f"  Additional capacity needed: {impact['additional_shelves']:,.0f} shelves")
        print(f"  Percent increase: {impact['percent_increase']:.1f}%")

    if not results:
        print("\nERROR: No results generated")
        return

    # Summary table
    print("\n\n" + "="*100)
    print("STORAGE IMPACT SUMMARY - ALL SCENARIOS")
    print("="*100)

    results_df = pd.DataFrame(results)

    print(f"\n{results_df[['scenario', 'avg_delay_per_delivery', 'avg_multiplier', 'baseline_shelves', 'estimated_shelves', 'additional_shelves', 'percent_increase']].to_string(index=False)}")

    # Save results
    output_file = RESULTS_DIR / "stochastic_storage_impact_estimates.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n\nResults saved to: {output_file}")

    # Key insights
    print("\n" + "="*100)
    print("KEY INSIGHTS: COST OF UNCERTAINTY")
    print("="*100)

    for _, row in results_df.iterrows():
        cost_of_uncertainty = row['additional_shelves']
        print(f"\n{row['scenario']}:")
        print(f"  Average delivery delay: {row['avg_delay_per_delivery']:.1f} days")
        print(f"  Storage requirement increase: {row['percent_increase']:.1f}%")
        print(f"  Additional shelves needed: {cost_of_uncertainty:,.0f}")
        print(f"  => Must expand {cost_of_uncertainty:,.0f} MORE shelves beyond baseline due to supply chain uncertainty")

    print("\n" + "="*100)
    print("FACILITY BREAKDOWN (Estimated)")
    print("="*100)
    print("\nBased on baseline split (Sacramento: 72%, Austin: 28%):")

    for _, row in results_df.iterrows():
        sac_additional = row['additional_shelves'] * 0.72
        austin_additional = row['additional_shelves'] * 0.28
        print(f"\n{row['scenario']}:")
        print(f"  Sacramento: +{sac_additional:,.0f} shelves (baseline: 2,884)")
        print(f"  Austin: +{austin_additional:,.0f} shelves (baseline: 1,110)")

if __name__ == "__main__":
    main()
