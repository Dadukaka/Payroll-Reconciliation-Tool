import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_synthetic_payroll_data(num_employees=100, month="2024-01"):
    """Generate synthetic SAP payroll register data"""
    
    np.random.seed(42)
    employee_ids = [f"EMP{str(i).zfill(5)}" for i in range(1, num_employees + 1)]
    
    departments = ['HR', 'Finance', 'IT', 'Operations', 'Sales']
    cost_centers = ['CC1001', 'CC1002', 'CC1003', 'CC1004', 'CC1005']
    
    data = {
        'Employee_ID': employee_ids,
        'Employee_Name': [f"Employee {i}" for i in range(1, num_employees + 1)],
        'Department': np.random.choice(departments, num_employees),
        'Cost_Center': np.random.choice(cost_centers, num_employees),
        'Base_Salary': np.random.uniform(3000, 10000, num_employees).round(2),
        'Overtime': np.random.uniform(0, 500, num_employees).round(2),
        'Bonus': np.random.choice([0, 500, 1000, 1500], num_employees),
        'Gross_Pay': 0,
        'Pension_Deduction': 0,
        'Health_Insurance': np.random.choice([200, 250, 300], num_employees),
        'Tax_Deduction': 0,
        'Total_Deductions': 0,
        'Net_Pay': 0,
        'Employer_Pension_Contribution': 0,
        'Employer_Benefits': 0,
        'Period': month
    }
    
    df = pd.DataFrame(data)
    
    # Calculate fields
    df['Gross_Pay'] = df['Base_Salary'] + df['Overtime'] + df['Bonus']
    df['Pension_Deduction'] = (df['Gross_Pay'] * 0.05).round(2)
    df['Tax_Deduction'] = (df['Gross_Pay'] * 0.15).round(2)
    df['Total_Deductions'] = df['Pension_Deduction'] + df['Health_Insurance'] + df['Tax_Deduction']
    df['Net_Pay'] = df['Gross_Pay'] - df['Total_Deductions']
    df['Employer_Pension_Contribution'] = (df['Gross_Pay'] * 0.06).round(2)
    df['Employer_Benefits'] = df['Health_Insurance'] * 0.8
    
    return df

def generate_gl_postings(payroll_df, introduce_variances=True):
    """Generate GL postings based on payroll with optional variances"""
    
    gl_entries = []
    
    # Aggregate by cost center
    summary = payroll_df.groupby('Cost_Center').agg({
        'Gross_Pay': 'sum',
        'Pension_Deduction': 'sum',
        'Health_Insurance': 'sum',
        'Tax_Deduction': 'sum',
        'Net_Pay': 'sum',
        'Employer_Pension_Contribution': 'sum',
        'Employer_Benefits': 'sum'
    }).reset_index()
    
    for _, row in summary.iterrows():
        cost_center = row['Cost_Center']
        
        # Gross Pay (Debit Salary Expense)
        variance_factor = np.random.uniform(0.98, 1.02) if introduce_variances and random.random() < 0.2 else 1.0
        gl_entries.append({
            'GL_Account': '6100',
            'Account_Description': 'Salary Expense',
            'Cost_Center': cost_center,
            'Debit': round(row['Gross_Pay'] * variance_factor, 2),
            'Credit': 0,
            'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
        })
        
        # Employee Pension (Credit Pension Payable)
        gl_entries.append({
            'GL_Account': '2110',
            'Account_Description': 'Pension Payable',
            'Cost_Center': cost_center,
            'Debit': 0,
            'Credit': round(row['Pension_Deduction'], 2),
            'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
        })
        
        # Employer Pension Contribution
        variance_factor = np.random.uniform(0.95, 1.0) if introduce_variances and random.random() < 0.15 else 1.0
        gl_entries.append({
            'GL_Account': '6120',
            'Account_Description': 'Employer Pension Expense',
            'Cost_Center': cost_center,
            'Debit': round(row['Employer_Pension_Contribution'] * variance_factor, 2),
            'Credit': 0,
            'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
        })
        
        # Health Insurance Payable
        gl_entries.append({
            'GL_Account': '2120',
            'Account_Description': 'Health Insurance Payable',
            'Cost_Center': cost_center,
            'Debit': 0,
            'Credit': round(row['Health_Insurance'], 2),
            'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
        })
        
        # Tax Payable
        gl_entries.append({
            'GL_Account': '2130',
            'Account_Description': 'Tax Payable',
            'Cost_Center': cost_center,
            'Debit': 0,
            'Credit': round(row['Tax_Deduction'], 2),
            'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
        })
        
        # Net Pay (Credit Cash/Bank)
        gl_entries.append({
            'GL_Account': '1010',
            'Account_Description': 'Cash - Payroll Account',
            'Cost_Center': cost_center,
            'Debit': 0,
            'Credit': round(row['Net_Pay'], 2),
            'Posting_Date': payroll_df['Period'].iloc[0] + '-30'
        })
    
    # Randomly omit some employer benefit accruals (introduce missing entries)
    if introduce_variances:
        for _, row in summary.iterrows():
            if random.random() > 0.3:  # 70% chance to include
                gl_entries.append({
                    'GL_Account': '6130',
                    'Account_Description': 'Employer Benefits Expense',
                    'Cost_Center': row['Cost_Center'],
                    'Debit': round(row['Employer_Benefits'], 2),
                    'Credit': 0,
                    'Posting_Date': payroll_df['Period'].iloc[0] + '-28'
                })
    
    return pd.DataFrame(gl_entries)

if __name__ == "__main__":
    # Generate sample data
    payroll = generate_synthetic_payroll_data(num_employees=100)
    gl = generate_gl_postings(payroll, introduce_variances=True)
    
    # Save to CSV
    payroll.to_csv('sample_payroll_register.csv', index=False)
    gl.to_csv('sample_gl_postings.csv', index=False)
    
    print("✅ Sample data generated!")
    print(f"Payroll records: {len(payroll)}")
    print(f"GL entries: {len(gl)}")