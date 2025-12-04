import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from reconciliation_engine import PayrollReconciliationEngine
from data_generator import generate_synthetic_payroll_data, generate_gl_postings

# Page config
st.set_page_config(
    page_title="Payroll Reconciliation Tool",
    page_icon="💰",
    layout="wide"
)

# Title
st.title("💰 Payroll Reconciliation Tool")
st.markdown("**SAP Payroll Register vs GL Postings Reconciliation**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📁 Data Upload")
    
    option = st.radio(
        "Choose data source:",
        ["Use Sample Data", "Upload Your Own Files"]
    )
    
    if option == "Use Sample Data":
        if st.button("Generate Sample Data"):
            with st.spinner("Generating synthetic data..."):
                payroll_df = generate_synthetic_payroll_data(num_employees=100)
                gl_df = generate_gl_postings(payroll_df, introduce_variances=True)
                
                st.session_state['payroll_df'] = payroll_df
                st.session_state['gl_df'] = gl_df
                st.success("✅ Sample data generated!")
    
    else:
        payroll_file = st.file_uploader("Upload Payroll Register (CSV/Excel)", type=['csv', 'xlsx'])
        gl_file = st.file_uploader("Upload GL Postings (CSV/Excel)", type=['csv', 'xlsx'])
        
        if payroll_file and gl_file:
            try:
                if payroll_file.name.endswith('.csv'):
                    payroll_df = pd.read_csv(payroll_file)
                else:
                    payroll_df = pd.read_excel(payroll_file)
                
                if gl_file.name.endswith('.csv'):
                    gl_df = pd.read_csv(gl_file)
                else:
                    gl_df = pd.read_excel(gl_file)
                
                st.session_state['payroll_df'] = payroll_df
                st.session_state['gl_df'] = gl_df
                st.success("✅ Files uploaded successfully!")
            except Exception as e:
                st.error(f"Error loading files: {e}")
    
    st.markdown("---")
    st.markdown("### 📊 About This Tool")
    st.markdown("""
    This tool performs automated reconciliation between:
    - SAP Payroll Register
    - GL Postings
    
    **Features:**
    - Variance detection
    - Missing accrual identification
    - Pension & benefit validation
    - Cost center balancing
    - Month-end/Year-end checks
    """)

# Main content
if 'payroll_df' in st.session_state and 'gl_df' in st.session_state:
    
    payroll_df = st.session_state['payroll_df']
    gl_df = st.session_state['gl_df']
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Data Preview", 
        "🔍 Reconciliation Results", 
        "📊 Variance Analysis",
        "📥 Export Report"
    ])
    
    with tab1:
        st.subheader("Payroll Register Data")
        st.dataframe(payroll_df.head(20), use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Employees", len(payroll_df))
        col2.metric("Total Gross Pay", f"${payroll_df['Gross_Pay'].sum():,.2f}")
        col3.metric("Total Net Pay", f"${payroll_df['Net_Pay'].sum():,.2f}")
        
        st.markdown("---")
        st.subheader("GL Postings Data")
        st.dataframe(gl_df.head(20), use_container_width=True)
        
        col1, col2 = st.columns(2)
        col1.metric("Total GL Entries", len(gl_df))
        col2.metric("Total Debits", f"${gl_df['Debit'].sum():,.2f}")
    
    with tab2:
        st.subheader("🔍 Reconciliation Results")
        
        if st.button("🚀 Run Reconciliation", type="primary"):
            with st.spinner("Running reconciliation checks..."):
                engine = PayrollReconciliationEngine(payroll_df, gl_df)
                results = engine.reconcile()
                st.session_state['results'] = results
        
        if 'results' in st.session_state:
            results = st.session_state['results']
            summary = results['summary']
            
            # Summary cards
            col1, col2, col3, col4 = st.columns(4)
            
            status_color = "🔴" if summary['Reconciliation_Status'] == 'FAILED' else "🟢"
            col1.metric(
                "Status", 
                f"{status_color} {summary['Reconciliation_Status']}"
            )
            col2.metric("Total Variances", summary['Total_Variances'])
            col3.metric("High Severity", summary['High_Severity_Count'])
            col4.metric("Total Variance $", f"${summary['Total_Variance_Amount']:,.2f}")
            
            st.markdown("---")
            
            # Variances
            if not results['variances'].empty:
                st.subheader("⚠️ Detected Variances")
                
                variance_df = results['variances'].copy()
                
                # Color code by severity
                def highlight_severity(row):
                    if row['Severity'] == 'High':
                        return ['background-color: #ffcccc'] * len(row)
                    elif row['Severity'] == 'Medium':
                        return ['background-color: #fff4cc'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(
                    variance_df.style.apply(highlight_severity, axis=1),
                    use_container_width=True
                )
            else:
                st.success("✅ No variances detected! Payroll and GL are fully reconciled.")
            
            # Flags
            if not results['flags'].empty:
                st.markdown("---")
                st.subheader("🚩 Action Items & Flags")
                
                for _, flag in results['flags'].iterrows():
                    with st.expander(f"⚠️ {flag['Category']}: {flag['Issue']}"):
                        st.write(f"**Impact:** {flag['Impact']}")
                        st.write(f"**Recommended Action:** {flag['Action']}")
            else:
                st.info("✅ No flags raised. All checks passed.")
    
    with tab3:
        st.subheader("📊 Variance Analysis")
        
        if 'results' in st.session_state and not st.session_state['results']['variances'].empty:
            variance_df = st.session_state['results']['variances']
            
            # Chart: Variance by Type
            fig1 = px.bar(
                variance_df,
                x='Type',
                y='Variance',
                color='Severity',
                title="Variance by Type",
                color_discrete_map={'High': '#ff4444', 'Medium': '#ffaa00', 'Low': '#44ff44'}
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Chart: Payroll vs GL Comparison
            comparison_data = variance_df[['Type', 'Payroll_Amount', 'GL_Amount']].melt(
                id_vars='Type',
                var_name='Source',
                value_name='Amount'
            )
            
            fig2 = px.bar(
                comparison_data,
                x='Type',
                y='Amount',
                color='Source',
                barmode='group',
                title="Payroll vs GL Amount Comparison"
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        else:
            st.info("Run reconciliation first to see variance analysis.")
    
    with tab4:
        st.subheader("📥 Export Reconciliation Report")
        
        if 'results' in st.session_state:
            results = st.session_state['results']
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not results['variances'].empty:
                    csv_variances = results['variances'].to_csv(index=False)
                    st.download_button(
                        label="📄 Download Variances (CSV)",
                        data=csv_variances,
                        file_name="payroll_variances.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if not results['flags'].empty:
                    csv_flags = results['flags'].to_csv(index=False)
                    st.download_button(
                        label="🚩 Download Flags (CSV)",
                        data=csv_flags,
                        file_name="reconciliation_flags.csv",
                        mime="text/csv"
                    )
            
            st.markdown("---")
            st.markdown("### 📋 Summary Report")
            st.json(results['summary'])
        else:
            st.info("Run reconciliation first to export reports.")

else:
    st.info("👈 Please generate sample data or upload your files using the sidebar.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Payroll Reconciliation Tool | Built with Streamlit</p>
    <p>Demonstrates GL posting validation, variance detection, and internal control checks</p>
</div>
""", unsafe_allow_html=True)