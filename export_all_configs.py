"""
Export ALL Phase 1 configurations with complete details
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv(r'C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking\packing_configurations.csv')

print('='*120)
print('PHASE 1: ALL PACKING CONFIGURATIONS - COMPLETE LISTING')
print('='*120)
print(f'\nTotal configurations: {df["Config_ID"].nunique()}')
print(f'Total records: {len(df)}')
print(f'Facilities: {df["Facility"].unique()}')
print(f'Storage types: {df["Storage_Type"].unique()}\n')

# Group by config and display each one
for config_id in sorted(df['Config_ID'].unique()):
    config_data = df[df['Config_ID'] == config_id]
    fac = config_data.iloc[0]['Facility']
    st = config_data.iloc[0]['Storage_Type']

    print(f'\n{"="*120}')
    print(f'CONFIG {config_id:3d}: {fac:<15} | {st:<10}')
    print(f'{"="*120}')
    print(f'{"SKU":<10} {"Packages/Shelf":>15} {"Vol/Pkg (cu ft)":>18} {"Wt/Pkg (lbs)":>16} {"Units/Pkg":>12} {"Total Vol":>12} {"Total Wt":>12}')
    print(f'{"-"*120}')

    total_packages = 0
    total_volume = 0
    total_weight = 0
    total_units = 0

    for _, row in config_data.iterrows():
        sku = row['SKU']
        packages = int(row['Packages_per_Shelf'])
        vol_per = row['Volume_per_Package']
        wt_per = row['Weight_per_Package']
        units_per = int(row['Units_per_Package'])
        total_vol = row['Total_Volume']
        total_wt = row['Total_Weight']

        print(f'{sku:<10} {packages:>15,} {vol_per:>18.4f} {wt_per:>16.2f} {units_per:>12,} {total_vol:>12.4f} {total_wt:>12.2f}')

        total_packages += packages
        total_volume += total_vol
        total_weight += total_wt
        total_units += packages * units_per

    print(f'{"-"*120}')
    print(f'{"TOTAL":<10} {total_packages:>15,} {"":>18} {"":>16} {total_units:>12,} {total_volume:>12.4f} {total_weight:>12.2f}')

print(f'\n{"="*120}')
print('END OF CONFIGURATIONS')
print(f'{"="*120}')

# Create summary statistics
print(f'\n{"="*120}')
print('SUMMARY STATISTICS')
print(f'{"="*120}')

print('\nConfigurations by Facility and Storage Type:')
summary = df.groupby(['Facility', 'Storage_Type'])['Config_ID'].nunique().reset_index()
summary.columns = ['Facility', 'Storage_Type', 'Num_Configs']
print(summary.to_string(index=False))

print('\nSKUs by Storage Type:')
sku_summary = df.groupby('Storage_Type')['SKU'].nunique().reset_index()
sku_summary.columns = ['Storage_Type', 'Unique_SKUs']
print(sku_summary.to_string(index=False))

print('\nAll SKUs in configurations:')
all_skus = sorted(df['SKU'].unique())
for i in range(0, len(all_skus), 6):
    print('  ' + ', '.join(all_skus[i:i+6]))
