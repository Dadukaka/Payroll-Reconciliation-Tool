import pandas as pd
import numpy as np

class PayrollReconciliationEngine:
    
    def __init__(self, payroll_df, gl_df):
        self.payroll_df = payroll_df
        self.gl_df = gl_df
        self.variances = []
        self.flags = []
        
    def reconcile(self):
        """Main reconciliation process"""
        self._check_totals()
        self._check_pension_deductions()
        self._check_benefit_accruals()
        self._check_retro_adjustments()
        self._validate_cost_center_balancing()
        
        return self._generate_report()
    
    def _check_totals(self):
        """Compare total payroll vs GL postings"""
        
        # Payroll totals
        total_gross = self.payroll_df['Gross_Pay'].sum()
        total_net = self.payroll_df['Net_Pay'].sum()
        total_deductions = self.payroll_df['Total_Deductions'].sum()
        
        # GL totals
        gl_salary_expense = self.gl_df[self.gl_df['GL_Account'] == '6100']['Debit'].sum()
        gl_cash_payout = self.gl_df[self.gl_df['GL_Account'] == '1010']['Credit'].sum()
        gl_total_liabilities = self.gl_df[
            self.gl_df['GL_Account'].isin(['2110', '2120', '2130'])
        ]['Credit'].sum()
        
        # Check variances
        gross_variance = total_gross - gl_salary_expense
        net_variance = total_net - gl_cash_payout
        deduction_variance = total_deductions - gl_total_liabilities
        
        if abs(gross_variance) > 0.01:
            self.variances.append({
                'Type': 'Gross Pay Variance',
                'Payroll_Amount': round(total_gross, 2),
                'GL_Amount': round(gl_salary_expense, 2),
                'Variance': round(gross_variance, 2),
                'Severity': 'High' if abs(gross_variance) > 100 else 'Medium'
            })
        
        if abs(net_variance) > 0.01:
            self.variances.append({
                'Type': 'Net Pay Variance',
                'Payroll_Amount': round(total_net, 2),
                'GL_Amount': round(gl_cash_payout, 2),
                'Variance': round(net_variance, 2),
                'Severity': 'High'
            })
        
        if abs(deduction_variance) > 0.01:
            self.variances.append({
                'Type': 'Total Deductions Variance',
                'Payroll_Amount': round(total_deductions, 2),
                'GL_Amount': round(gl_total_liabilities, 2),
                'Variance': round(deduction_variance, 2),
                'Severity': 'Medium'
            })
    
    def _check_pension_deductions(self):
        """Validate pension deductions and employer contributions"""
        
        # Employee pension
        payroll_pension = self.payroll_df['Pension_Deduction'].sum()
        gl_pension_payable = self.gl_df[self.gl_df['GL_Account'] == '2110']['Credit'].sum()
        pension_variance = payroll_pension - gl_pension_payable
        
        if abs(pension_variance) > 0.01:
            self.variances.append({
                'Type': 'Pension Deduction Variance',
                'Payroll_Amount': round(payroll_pension, 2),
                'GL_Amount': round(gl_pension_payable, 2),
                'Variance': round(pension_variance, 2),
                'Severity': 'High'
            })
        
        # Employer pension contribution
        payroll_employer_pension = self.payroll_df['Employer_Pension_Contribution'].sum()
        gl_employer_pension = self.gl_df[self.gl_df['GL_Account'] == '6120']['Debit'].sum()
        employer_variance = payroll_employer_pension - gl_employer_pension
        
        if abs(employer_variance) > 0.01:
            self.variances.append({
                'Type': 'Employer Pension Contribution Variance',
                'Payroll_Amount': round(payroll_employer_pension, 2),
                'GL_Amount': round(gl_employer_pension, 2),
                'Variance': round(employer_variance, 2),
                'Severity': 'High'
            })
            self.flags.append({
                'Category': 'Pension',
                'Issue': 'Employer pension contribution not fully accrued in GL',
                'Impact': f'Understated expense by ${abs(employer_variance):.2f}',
                'Action': 'Post accrual adjustment before month-end close'
            })
    
    def _check_benefit_accruals(self):
        """Check if employer benefits are properly accrued"""
        
        payroll_employer_benefits = self.payroll_df['Employer_Benefits'].sum()
        gl_benefits_expense = self.gl_df[self.gl_df['GL_Account'] == '6130']['Debit'].sum()
        benefits_variance = payroll_employer_benefits - gl_benefits_expense
        
        if abs(benefits_variance) > 0.01:
            self.flags.append({
                'Category': 'Benefits Accrual',
                'Issue': 'Missing or incomplete employer benefit accruals',
                'Impact': f'Understated expense by ${abs(benefits_variance):.2f}',
                'Action': 'Review and post missing benefit accrual entries'
            })
            
            self.variances.append({
                'Type': 'Employer Benefits Variance',
                'Payroll_Amount': round(payroll_employer_benefits, 2),
                'GL_Amount': round(gl_benefits_expense, 2),
                'Variance': round(benefits_variance, 2),
                'Severity': 'High'
            })
    
    def _check_retro_adjustments(self):
        """Flag potential retroactive adjustments"""
        
        # Check for unusually high bonuses or overtime (potential retro)
        high_bonus = self.payroll_df[self.payroll_df['Bonus'] > 1000]
        high_overtime = self.payroll_df[self.payroll_df['Overtime'] > 400]
        
        if len(high_bonus) > 0:
            self.flags.append({
                'Category': 'Retro Adjustment',
                'Issue': f'{len(high_bonus)} employees with high bonuses (>$1,000)',
                'Impact': 'Potential retroactive pay adjustments',
                'Action': 'Verify if bonuses relate to prior periods and adjust accruals'
            })
        
        if len(high_overtime) > 0:
            self.flags.append({
                'Category': 'Retro Adjustment',
                'Issue': f'{len(high_overtime)} employees with high overtime (>$400)',
                'Impact': 'May indicate prior period corrections',
                'Action': 'Review for proper period allocation'
            })
    
    def _validate_cost_center_balancing(self):
        """Ensure each cost center balances"""
        
        for cost_center in self.payroll_df['Cost_Center'].unique():
            cc_payroll = self.payroll_df[self.payroll_df['Cost_Center'] == cost_center]
            cc_gl = self.gl_df[self.gl_df['Cost_Center'] == cost_center]
            
            payroll_gross = cc_payroll['Gross_Pay'].sum()
            gl_expense = cc_gl[cc_gl['GL_Account'] == '6100']['Debit'].sum()
            
            variance = payroll_gross - gl_expense
            
            if abs(variance) > 0.01:
                self.variances.append({
                    'Type': f'Cost Center {cost_center} Variance',
                    'Payroll_Amount': round(payroll_gross, 2),
                    'GL_Amount': round(gl_expense, 2),
                    'Variance': round(variance, 2),
                    'Severity': 'Medium'
                })
    
    def _generate_report(self):
        """Generate reconciliation report"""
        
        variance_df = pd.DataFrame(self.variances) if self.variances else pd.DataFrame()
        flags_df = pd.DataFrame(self.flags) if self.flags else pd.DataFrame()
        
        # Summary stats
        total_variances = len(self.variances)
        high_severity = len([v for v in self.variances if v.get('Severity') == 'High'])
        total_variance_amount = sum([abs(v['Variance']) for v in self.variances])
        
        summary = {
            'Total_Variances': total_variances,
            'High_Severity_Count': high_severity,
            'Total_Variance_Amount': round(total_variance_amount, 2),
            'Total_Flags': len(self.flags),
            'Reconciliation_Status': 'FAILED' if total_variances > 0 else 'PASSED'
        }
        
        return {
            'summary': summary,
            'variances': variance_df,
            'flags': flags_df
        }