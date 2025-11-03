"""
List all Pallet configurations from Phase 1
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv(r'C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking\packing_configurations.csv')
pallet_df = df[df['Storage_Type'] == 'Pallet'].sort_values(['Facility', 'Config_ID'])

print('='*100)
print('PHASE 1 PALLET CONFIGURATIONS - COMPLETE LIST')
print('='*100)
print(f'\nTotal pallet configurations: {pallet_df["Config_ID"].nunique()}')
print(f'Total packing records: {len(pallet_df)}\n')

for config_id in sorted(pallet_df['Config_ID'].unique()):
    config_data = pallet_df[pallet_df['Config_ID'] == config_id]
    fac = config_data.iloc[0]['Facility']

    print(f'\n{"="*100}')
    print(f'CONFIG {config_id}: {fac} - Pallet')
    print(f'{"="*100}')
    print(f'  {"SKU":<10} {"Packages":<12} {"Vol/Pkg":<12} {"Wt/Pkg":<12} {"Units/Pkg":<12} {"Total Vol":<12} {"Total Wt":<12}')
    print(f'  {"-"*90}')

    total_packages = 0
    total_volume = 0
    total_weight = 0

    for _, row in config_data.iterrows():
        sku = row['SKU']
        packages = int(row['Packages_per_Shelf'])
        vol_per = row['Volume_per_Package']
        wt_per = row['Weight_per_Package']
        units_per = int(row['Units_per_Package'])
        total_vol = row['Total_Volume']
        total_wt = row['Total_Weight']

        print(f'  {sku:<10} {packages:>8}        {vol_per:>8.2f}      {wt_per:>8.1f}      {units_per:>8}        {total_vol:>8.2f}      {total_wt:>8.1f}')

        total_packages += packages
        total_volume += total_vol
        total_weight += total_wt

    print(f'  {"-"*90}')
    print(f'  {"TOTAL":<10} {total_packages:>8}                                                  {total_volume:>8.2f}      {total_weight:>8.1f}')

    # Calculate utilization (assuming 600 lbs max)
    weight_util = (total_weight / 600.0) * 100
    print(f'\n  Weight Utilization: {weight_util:.1f}% of 600 lbs max capacity')

print(f'\n{"="*100}')
print('SUMMARY BY FACILITY')
print(f'{"="*100}')

for fac in ['Austin', 'Columbus', 'Sacramento']:
    fac_configs = pallet_df[pallet_df['Facility'] == fac]['Config_ID'].nunique()
    print(f'  {fac}: {fac_configs} pallet configurations')
