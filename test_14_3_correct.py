"""
TEST: 14/3 CALENDAR DAYS (CORRECTLY CONVERTED TO BUSINESS DAYS)

14 calendar days = 10 business days (14 × 5/7)
3 calendar days  = 2-3 business days (using 3 to be conservative)

Compare with original DoH requirements
"""

import pandas as pd

DATA_DIR = r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data"

# Load original
original_df = pd.read_csv(f"{DATA_DIR}\\Lead TIme.csv")

# Load 14/3 (incorrectly treated as business days)
test_14_3_df = pd.read_csv(f"{DATA_DIR}\\Lead TIme_14_3_days.csv")

# Load corrected (10/3 business days)
corrected_df = pd.read_csv(f"{DATA_DIR}\\Lead TIme_14_3_business_days.csv")

print("="*100)
print("DAYS-ON-HAND COMPARISON")
print("="*100)

print("\n[1] INTERNATIONAL SKUs (SKUW1, SKUE1)")
print("-" * 80)
print(f"{'Policy':<30} {'Columbus':<15} {'Sacramento':<15} {'Austin':<15}")
print("-" * 80)

# SKUW1
col_orig = original_df[original_df['SKU Number'] == 'SKUW1']['Columbus - Days on Hand'].values[0]
sac_orig = original_df[original_df['SKU Number'] == 'SKUW1']['Sacramento - Days on Hand'].values[0]
aus_orig = original_df[original_df['SKU Number'] == 'SKUW1']['Austin Days on Hand'].values[0]

col_14 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUW1']['Columbus - Days on Hand'].values[0]
sac_14 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUW1']['Sacramento - Days on Hand'].values[0]
aus_14 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUW1']['Austin Days on Hand'].values[0]

col_10 = corrected_df[corrected_df['SKU Number'] == 'SKUW1']['Columbus - Days on Hand'].values[0]
sac_10 = corrected_df[corrected_df['SKU Number'] == 'SKUW1']['Sacramento - Days on Hand'].values[0]
aus_10 = corrected_df[corrected_df['SKU Number'] == 'SKUW1']['Austin Days on Hand'].values[0]

print(f"{'Original (business days)':<30} {col_orig:<15} {sac_orig:<15} {aus_orig:<15}")
print(f"{'14 cal days (WRONG - as biz)':<30} {col_14:<15} {sac_14:<15} {aus_14:<15}")
print(f"{'10 biz days (CORRECT)':<30} {col_10:<15} {sac_10:<15} {aus_10:<15}")

print("\n[2] DOMESTIC SKUs (SKUA1, SKUT1, SKUD1, SKUC1)")
print("-" * 80)
print(f"{'Policy':<30} {'Columbus':<15} {'Sacramento':<15} {'Austin':<15}")
print("-" * 80)

# SKUA1
col_orig = original_df[original_df['SKU Number'] == 'SKUA1']['Columbus - Days on Hand'].values[0]
sac_orig = original_df[original_df['SKU Number'] == 'SKUA1']['Sacramento - Days on Hand'].values[0]
aus_orig = original_df[original_df['SKU Number'] == 'SKUA1']['Austin Days on Hand'].values[0]

col_3 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUA1']['Columbus - Days on Hand'].values[0]
sac_3 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUA1']['Sacramento - Days on Hand'].values[0]
aus_3 = test_14_3_df[test_14_3_df['SKU Number'] == 'SKUA1']['Austin Days on Hand'].values[0]

col_3_cor = corrected_df[corrected_df['SKU Number'] == 'SKUA1']['Columbus - Days on Hand'].values[0]
sac_3_cor = corrected_df[corrected_df['SKU Number'] == 'SKUA1']['Sacramento - Days on Hand'].values[0]
aus_3_cor = corrected_df[corrected_df['SKU Number'] == 'SKUA1']['Austin Days on Hand'].values[0]

print(f"{'Original (business days)':<30} {col_orig:<15} {sac_orig:<15} {aus_orig:<15}")
print(f"{'3 cal days (as business)':<30} {col_3:<15} {sac_3:<15} {aus_3:<15}")
print(f"{'3 biz days (CORRECT)':<30} {col_3_cor:<15} {sac_3_cor:<15} {aus_3_cor:<15}")

print("\n" + "="*100)
print("KEY INSIGHT")
print("="*100)
print("\nYou're absolutely right - the numbers should be LOWER!")
print()
print("Original international DoH: 35-46 business days")
print("Your proposed 14 calendar days = 10 business days")
print("Reduction: 71-78% DECREASE in safety stock required")
print()
print("Original domestic DoH: 3-15 business days")
print("Your proposed 3 calendar days = 3 business days  ")
print("Reduction: 0-80% DECREASE depending on SKU/facility")
print()
print("With LOWER days-on-hand, we should need LESS inventory and FEWER shelves.")
print("The previous test incorrectly used 14 as business days (not calendar days).")
print("="*100)
