"""
visualize_trucking.py

Visualizations for trucking data with columns:
    Month, Day, Facility, Supplier, Num_Trucks

Usage:
    1. Ensure truck_dispatch_integer_3_1_doh.csv is in the parent folder.
    2. Run:  python visualize_trucking.py
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np


DATA_PATH_PARTIAL = Path(__file__).parent / "trucking_data_partial.csv"
DATA_PATH_FULL = Path(__file__).parent.parent / "truck_dispatch_integer_3_1_doh.csv"


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Make sure trucking_data_partial.csv is in the same folder."
        )

    df = pd.read_csv(path)

    # Basic cleaning / type enforcement
    df["Day"] = df["Day"].astype(int)
    df["Trucks_Needed"] = df["Trucks_Needed"].astype(int)

    return df


def load_full_data(path: Path) -> pd.DataFrame:
    """Load the full truck dispatch data with Month, Day, Facility, Supplier, Num_Trucks columns."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Make sure truck_dispatch_integer_3_1_doh.csv is in the parent folder."
        )

    df = pd.read_csv(path)

    # Basic cleaning / type enforcement
    df["Month"] = df["Month"].astype(int)
    df["Day"] = df["Day"].astype(int)
    df["Num_Trucks"] = df["Num_Trucks"].astype(float)

    return df


def plot_total_trucks_per_day(df: pd.DataFrame) -> None:
    """Total trucks needed per day across all facilities and suppliers."""
    daily = df.groupby("Day")["Trucks_Needed"].sum().reset_index()

    plt.figure(figsize=(10, 4))
    plt.plot(daily["Day"], daily["Trucks_Needed"], marker="o")
    plt.title("Total Trucks Needed per Day (All Facilities)")
    plt.xlabel("Day")
    plt.ylabel("Trucks Needed")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()


def plot_trucks_per_day_by_facility(df: pd.DataFrame) -> None:
    """Line chart of total trucks per day, split by facility."""
    facility_daily = (
        df.groupby(["Day", "Facility"])["Trucks_Needed"]
        .sum()
        .reset_index()
        .pivot(index="Day", columns="Facility", values="Trucks_Needed")
    )

    plt.figure(figsize=(10, 5))
    for facility in facility_daily.columns:
        plt.plot(
            facility_daily.index,
            facility_daily[facility],
            marker="o",
            label=facility,
        )

    plt.title("Total Trucks per Day by Facility")
    plt.xlabel("Day")
    plt.ylabel("Trucks Needed")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Facility")
    plt.tight_layout()


def plot_supplier_share_by_facility(df: pd.DataFrame) -> None:
    """
    Stacked bar chart: for each facility, how many trucks each supplier contributes
    (summed across all days).
    """
    facility_supplier = (
        df.groupby(["Facility", "Supplier"])["Trucks_Needed"]
        .sum()
        .reset_index()
        .pivot(index="Facility", columns="Supplier", values="Trucks_Needed")
        .fillna(0)
    )

    ax = facility_supplier.plot(
        kind="bar",
        stacked=True,
        figsize=(10, 5),
    )

    plt.title("Trucks Needed by Supplier at Each Facility (Total over All Days)")
    plt.xlabel("Facility")
    plt.ylabel("Total Trucks Needed")
    plt.xticks(rotation=0)
    plt.legend(title="Supplier", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()


def plot_heatmap_day_vs_facility(df: pd.DataFrame) -> None:
    """
    Heatmap: total trucks per day & facility (summed over suppliers).
    """
    day_facility = (
        df.groupby(["Day", "Facility"])["Trucks_Needed"]
        .sum()
        .reset_index()
        .pivot(index="Day", columns="Facility", values="Trucks_Needed")
        .fillna(0)
    )

    plt.figure(figsize=(8, 6))
    plt.imshow(day_facility.T, aspect="auto", origin="lower")
    plt.colorbar(label="Trucks Needed")
    plt.title("Heatmap: Trucks Needed by Day and Facility")
    plt.yticks(range(len(day_facility.columns)), day_facility.columns)
    plt.xticks(range(len(day_facility.index)), day_facility.index)
    plt.xlabel("Day")
    plt.ylabel("Facility")
    plt.tight_layout()


def plot_year10_heatmap_by_facility(df_full: pd.DataFrame) -> None:
    """
    Heatmap for Year 10 (months 109-120) showing trucks needed by continuous day and facility.
    Similar format to original heatmap but extended to all 252 days of Year 10.
    """
    # Filter for Year 10 (months 109-120)
    df_year10 = df_full[df_full['Month'].between(109, 120)].copy()

    # Create continuous day index for Year 10 (1-252)
    df_year10['Continuous_Day'] = (df_year10['Month'] - 109) * 21 + df_year10['Day']

    # Group by Continuous_Day, Facility and sum Num_Trucks
    day_facility = (
        df_year10.groupby(['Continuous_Day', 'Facility'])['Num_Trucks']
        .sum()
        .reset_index()
        .pivot(index='Continuous_Day', columns='Facility', values='Num_Trucks')
        .fillna(0)
    )

    plt.figure(figsize=(20, 6))
    plt.imshow(day_facility.T, aspect='auto', origin='lower')
    plt.colorbar(label='Trucks Needed')
    plt.title('Year 10 Heatmap: Trucks Needed by Day and Facility', fontsize=14, fontweight='bold')
    plt.yticks(range(len(day_facility.columns)), day_facility.columns)

    # Show every 21st day (beginning of each month)
    xtick_positions = range(0, len(day_facility.index), 21)
    xtick_labels = [f"M{109 + i}" for i in range(12)]
    plt.xticks(xtick_positions, xtick_labels)

    plt.xlabel('Day (Year 10)', fontsize=12)
    plt.ylabel('Facility', fontsize=12)
    plt.tight_layout()


def main():
    # Load partial data (first few days)
    df = load_data(DATA_PATH_PARTIAL)

    # 1. Total per day
    plot_total_trucks_per_day(df)

    # 2. Total per day by facility
    plot_trucks_per_day_by_facility(df)

    # 3. Supplier mix by facility (stacked bar)
    plot_supplier_share_by_facility(df)

    # 4. Heatmap (day x facility)
    plot_heatmap_day_vs_facility(df)

    # Load full data for Year 10 heatmap
    df_full = load_full_data(DATA_PATH_FULL)

    # 5. Year 10 heatmap (extended timeline)
    plot_year10_heatmap_by_facility(df_full)

    # Show all figures
    plt.show()


if __name__ == "__main__":
    main()
