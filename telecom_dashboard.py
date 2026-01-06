import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="ConnectUAE Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .metric-card {padding: 20px; border-radius: 10px; background: #f0f2f6; margin: 10px 0;}
    .insight-box {padding: 20px; border-radius: 10px; background: #f8f9fa; border-left: 5px solid #28a745; border: 1px solid #dee2e6; color: #212529;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_and_clean_data():
    """Load and clean all datasets"""
    # Load data
    subscribers = pd.read_csv('subscribers.csv')
    usage = pd.read_csv('usage_records.csv')
    billing = pd.read_csv('billing.csv')
    tickets = pd.read_csv('tickets.csv')
    outages = pd.read_csv('network_outages.csv')
    
    # CLEANING STEPS
    
    # 1. Remove duplicates
    subscribers = subscribers.drop_duplicates(subset='subscriber_id', keep='first')
    billing = billing.drop_duplicates(subset='bill_id', keep='first')
    tickets = tickets.drop_duplicates(subset='ticket_id', keep='first')
    
    # 2. Standardize labels
    subscribers['plan_type'] = subscribers['plan_type'].str.strip().str.lower().str.replace('-', '').str.capitalize()
    subscribers.loc[subscribers['plan_type'].str.contains('pre', case=False, na=False), 'plan_type'] = 'Prepaid'
    subscribers.loc[subscribers['plan_type'].str.contains('post', case=False, na=False), 'plan_type'] = 'Postpaid'
    
    subscribers['city'] = subscribers['city'].str.replace('-', ' ').str.replace('AbuDhabi', 'Abu Dhabi')
    subscribers.loc[subscribers['city'] == 'AD', 'city'] = 'Abu Dhabi'
    
    tickets['status'] = tickets['status'].str.strip().str.capitalize()
    tickets.loc[tickets['status'] == 'Closed', 'status'] = 'Resolved'
    
    # 3. Impute missing data_usage_gb
    subscriber_avg = usage.groupby('subscriber_id')['data_usage_gb'].mean()
    for idx in usage[usage['data_usage_gb'].isna()].index:
        sub_id = usage.at[idx, 'subscriber_id']
        if sub_id in subscriber_avg.index and not pd.isna(subscriber_avg[sub_id]):
            usage.at[idx, 'data_usage_gb'] = subscriber_avg[sub_id]
        else:
            usage.at[idx, 'data_usage_gb'] = 0
    
    # 4. Cap outliers
    usage.loc[usage['data_usage_gb'] > 100, 'data_usage_gb'] = 100
    billing.loc[billing['bill_amount'] > 2000, 'bill_amount'] = 2000
    
    # 5. Remove impossible date sequences
    tickets['ticket_date'] = pd.to_datetime(tickets['ticket_date'])
    tickets['resolution_date'] = pd.to_datetime(tickets['resolution_date'], errors='coerce')
    tickets.loc[tickets['resolution_date'] < tickets['ticket_date'], 'resolution_date'] = pd.NaT
    
    usage['usage_date'] = pd.to_datetime(usage['usage_date'], errors='coerce')
    subscribers['activation_date'] = pd.to_datetime(subscribers['activation_date'], errors='coerce')
    usage = usage.merge(subscribers[['subscriber_id', 'activation_date']], on='subscriber_id', how='left')
    usage = usage[usage['usage_date'] >= usage['activation_date']]
    usage = usage.drop('activation_date', axis=1)
    
    # 6. Remove negative bills
    billing = billing[billing['bill_amount'] >= 0]
    
    # 7. Calculate missing outage durations
    outages['outage_start_time'] = pd.to_datetime(outages['outage_start_time'], errors='coerce')
    outages['outage_end_time'] = pd.to_datetime(outages['outage_end_time'], errors='coerce')
    missing_duration = outages['outage_duration_mins'].isna()
    outages.loc[missing_duration, 'outage_duration_mins'] = (
        (outages.loc[missing_duration, 'outage_end_time'] - 
         outages.loc[missing_duration, 'outage_start_time']).dt.total_seconds() / 60
    )
    
    # Convert dates
    billing['billing_month'] = pd.to_datetime(billing['billing_month'])
    billing['payment_date'] = pd.to_datetime(billing['payment_date'], errors='coerce')
    outages['outage_date'] = pd.to_datetime(outages['outage_date'], errors='coerce')
    
    # Calculate subscriber tenure
    subscribers['tenure_years'] = (datetime.now() - subscribers['activation_date']).dt.days / 365.25
    
    return subscribers, usage, billing, tickets, outages

def calculate_service_tier(row):
    """Rule-based service tier classification"""
    if (row['plan_type'] == 'Postpaid' and row['plan_name'] == 'Unlimited') or row['tenure_years'] > 3:
        return 'Priority 1 (Critical)'
    elif (row['plan_type'] == 'Postpaid' and row['plan_name'] == 'Premium') or row['tenure_years'] > 1:
        return 'Priority 2 (High)'
    elif row['plan_type'] == 'Postpaid':
        return 'Priority 3 (Standard)'
    else:
        return 'Priority 4 (Basic)'

def main():
    st.title("🌐 ConnectUAE - Telecom Dashboard")
    st.markdown("**Revenue & Service Operations Analytics**")
    
    # Load data
    try:
        subscribers, usage, billing, tickets, outages = load_and_clean_data()
    except FileNotFoundError:
        st.error("⚠️ Data files not found! Please run `python data_generator.py` first.")
        return
    
    # Add service tier
    subscribers['service_tier'] = subscribers.apply(calculate_service_tier, axis=1)
    
    # Merge tickets with subscriber info
    tickets = tickets.merge(
        subscribers[['subscriber_id', 'city', 'zone', 'plan_type', 'service_tier']], 
        on='subscriber_id', 
        how='left',
        suffixes=('', '_sub')
    )
    if 'city_sub' in tickets.columns:
        tickets['city'] = tickets['city'].fillna(tickets['city_sub'])
        tickets['zone'] = tickets['zone'].fillna(tickets['zone_sub'])
        tickets = tickets.drop(['city_sub', 'zone_sub'], axis=1)
    
    # SIDEBAR FILTERS
    st.sidebar.header("🔍 Filters")
    
    # Date range
    min_date = min(tickets['ticket_date'].min(), billing['billing_month'].min())
    max_date = max(tickets['ticket_date'].max(), billing['billing_month'].max())
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # City filter
    cities = st.sidebar.multiselect(
        "City",
        options=sorted(subscribers['city'].unique()),
        default=sorted(subscribers['city'].unique())
    )
    
    # Plan type
    plan_types = st.sidebar.multiselect(
        "Plan Type",
        options=['Prepaid', 'Postpaid'],
        default=['Prepaid', 'Postpaid']
    )
    
    # Plan name
    plan_names = st.sidebar.multiselect(
        "Plan Name",
        options=sorted(subscribers['plan_name'].unique()),
        default=sorted(subscribers['plan_name'].unique())
    )
    
    # Ticket category
    ticket_cats = st.sidebar.multiselect(
        "Ticket Category",
        options=sorted(tickets['ticket_category'].unique()),
        default=sorted(tickets['ticket_category'].unique())
    )
    
    # Subscriber status
    sub_status = st.sidebar.multiselect(
        "Subscriber Status",
        options=['Active', 'Suspended', 'Churned'],
        default=['Active', 'Suspended', 'Churned']
    )
    
    st.sidebar.markdown("---")
    
    # VIEW TOGGLE
    view_mode = st.sidebar.radio(
        "📊 Dashboard View",
        options=["Executive View", "Manager View"],
        index=0
    )
    
    # Apply filters
    if len(date_range) == 2:
        start_dt, end_dt = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start_dt, end_dt = min_date, max_date
    
    # Initial filter based on static attributes
    filtered_subs_initial = subscribers[
        (subscribers['city'].isin(cities)) &
        (subscribers['plan_type'].isin(plan_types)) &
        (subscribers['plan_name'].isin(plan_names)) &
        (subscribers['status'].isin(sub_status))
    ]
    
    # Get all subscriber IDs that have activity during the selected date range
    # This includes billing, ticket, and outage-related activities
    billing_sub_ids = set(billing[
        (billing['subscriber_id'].isin(filtered_subs_initial['subscriber_id'])) &
        (billing['billing_month'] >= start_dt) &
        (billing['billing_month'] <= end_dt)
    ]['subscriber_id'].unique())
    
    ticket_sub_ids = set(tickets[
        (tickets['subscriber_id'].isin(filtered_subs_initial['subscriber_id'])) &
        (tickets['ticket_date'] >= start_dt) &
        (tickets['ticket_date'] <= end_dt)
    ]['subscriber_id'].unique())
    
    # Combine all active subscriber IDs during the date range
    active_sub_ids = billing_sub_ids.union(ticket_sub_ids)
    
    # If no date-filtered activity, fall back to initial filter
    if len(active_sub_ids) > 0:
        filtered_subs = filtered_subs_initial[filtered_subs_initial['subscriber_id'].isin(active_sub_ids)].copy()
    else:
        filtered_subs = filtered_subs_initial.copy()
    
    # Now filter the related data based on the final filtered subscribers
    filtered_billing = billing[
        (billing['subscriber_id'].isin(filtered_subs['subscriber_id'])) &
        (billing['billing_month'] >= start_dt) &
        (billing['billing_month'] <= end_dt)
    ]
    
    filtered_tickets = tickets[
        (tickets['city'].isin(cities)) &
        (tickets['plan_type'].isin(plan_types)) &
        (tickets['ticket_category'].isin(ticket_cats)) &
        (tickets['ticket_date'] >= start_dt) &
        (tickets['ticket_date'] <= end_dt)
    ]
    
    filtered_outages = outages[
        (outages['city'].isin(cities)) &
        (outages['outage_date'] >= start_dt) &
        (outages['outage_date'] <= end_dt)
    ]
    
    # EXECUTIVE VIEW
    if view_mode == "Executive View":
        st.header("💼 Executive Dashboard")
        
        # Calculate KPIs
        total_revenue = filtered_billing['bill_amount'].sum()
        active_count = filtered_subs[filtered_subs['status'] == 'Active'].shape[0]
        arpu = total_revenue / active_count if active_count > 0 else 0
        
        # Retention ratio (simplified as active vs total)
        # Calculate retention ratio based on active subscribers in the filtered data
        total_filtered_subs = len(filtered_subs)
        active_filtered_subs = len(filtered_subs[filtered_subs['status'] == 'Active'])
        retention_ratio = (active_filtered_subs / total_filtered_subs * 100) if total_filtered_subs > 0 else 0
        
        overdue_revenue = filtered_billing[filtered_billing['payment_status'] == 'Overdue']['bill_amount'].sum()
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Revenue", f"AED {total_revenue:,.0f}")
        with col2:
            st.metric("ARPU", f"AED {arpu:,.2f}")
        with col3:
            st.metric("Retention Ratio", f"{retention_ratio:.1f}%")
        with col4:
            st.metric("Overdue Revenue", f"AED {overdue_revenue:,.0f}")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Monthly ARPU Trend
            monthly_data = filtered_billing.copy()
            monthly_data['month'] = monthly_data['billing_month'].dt.to_period('M').astype(str)
            monthly_rev = monthly_data.groupby('month')['bill_amount'].sum()
            monthly_subs = filtered_subs[filtered_subs['status'] == 'Active'].shape[0]
            monthly_arpu = monthly_rev / monthly_subs if monthly_subs > 0 else monthly_rev * 0
            
            # Create a DataFrame for the ARPU data
            arpu_df = pd.DataFrame({
                'month': monthly_arpu.index,
                'arpu': monthly_arpu.values
            })
            
            fig1 = px.line(
                arpu_df,
                x='month',
                y='arpu',
                title="Monthly ARPU Trend",
                labels={'x': 'Month', 'y': 'ARPU (AED)'}
            )
            fig1.update_traces(mode='lines+markers')
            fig1.add_annotation(text="Shows ARPU trends over time. Look for seasonal patterns or declining trends.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig1, width='stretch')
            
            # Insights for ARPU chart
            if len(monthly_arpu) > 0:
                latest_arpu = monthly_arpu.values[-1]
                st.caption(f"Latest ARPU: AED {latest_arpu:,.2f}")
        
        with col2:
            # Revenue by Plan Type by Month
            rev_by_plan = filtered_billing.merge(
                filtered_subs[['subscriber_id', 'plan_type']], 
                on='subscriber_id'
            )
            rev_by_plan['month'] = rev_by_plan['billing_month'].dt.to_period('M').astype(str)
            rev_pivot = rev_by_plan.groupby(['month', 'plan_type'])['bill_amount'].sum().reset_index()
            
            fig2 = px.bar(
                rev_pivot,
                x='month',
                y='bill_amount',
                color='plan_type',
                title="Revenue by Plan Type (Monthly)",
                labels={'bill_amount': 'Revenue (AED)', 'month': 'Month'},
                barmode='stack'
            )
            fig2.add_annotation(text="Compare revenue contribution of different plan types over time.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig2, width='stretch')
            
            # Insights for revenue by plan
            if len(rev_pivot) > 0:
                top_plan = rev_pivot.groupby('plan_type')['bill_amount'].sum().idxmax()
                st.caption(f"Top performing plan: {top_plan}")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Revenue by City
            city_rev = filtered_billing.merge(
                filtered_subs[['subscriber_id', 'city']], 
                on='subscriber_id'
            ).groupby('city')['bill_amount'].sum().sort_values(ascending=True)
            
            # Create a DataFrame for the city revenue data
            city_rev_df = pd.DataFrame({
                'revenue': city_rev.values,
                'city': city_rev.index
            })
            
            fig3 = px.bar(
                city_rev_df,
                x='revenue',
                y='city',
                orientation='h',
                title="Revenue by City",
                labels={'x': 'Revenue (AED)', 'y': 'City'}
            )
            fig3.add_annotation(text="Identify highest and lowest revenue-generating cities.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig3, width='stretch')
            
            # Insights for revenue by city
            if len(city_rev) > 0:
                top_city = city_rev.index[-1]
                top_city_rev = city_rev.iloc[-1]
                st.caption(f"Top revenue city: {top_city} (AED {top_city_rev:,.0f})")
        
        with col4:
            # Payment Status Distribution
            payment_dist = filtered_billing['payment_status'].value_counts()
            
            fig4 = px.pie(
                values=payment_dist.values,
                names=payment_dist.index,
                title="Payment Status Distribution"
            )
            fig4.add_annotation(text="Visualize payment status distribution and identify overdue accounts.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig4, width='stretch')
            
            # Insights for payment status
            if 'Overdue' in payment_dist.index:
                overdue_pct = (payment_dist['Overdue'] / payment_dist.sum()) * 100
                st.caption(f"Overdue accounts: {overdue_pct:.1f}% of total")
        
        # Insights Box
        st.markdown("### 💡 Executive Insights")
        postpaid_rev = filtered_billing.merge(
            filtered_subs[filtered_subs['plan_type'] == 'Postpaid'][['subscriber_id']], 
            on='subscriber_id'
        )['bill_amount'].sum()
        postpaid_pct = (postpaid_rev / total_revenue * 100) if total_revenue > 0 else 0
        
        top_overdue_city = filtered_billing[filtered_billing['payment_status'] == 'Overdue'].merge(
            filtered_subs[['subscriber_id', 'city']], 
            on='subscriber_id'
        ).groupby('city')['bill_amount'].sum().idxmax() if overdue_revenue > 0 else "N/A"
        
        insight_text = f"""
        **Key Findings:**
        - ARPU is AED {arpu:,.2f}, with {postpaid_pct:.1f}% from Postpaid plans
        - Retention ratio is {retention_ratio:.1f}%
        - AED {overdue_revenue:,.0f} is at risk from overdue accounts
        - Highest overdue concentration: {top_overdue_city}
        - Total credit adjustments: AED {filtered_billing['credit_adjustment'].sum():,.0f}
        """
        st.markdown(f'<div class="insight-box">{insight_text}</div>', unsafe_allow_html=True)
    
    # MANAGER VIEW
    else:
        st.header("⚙️ Manager Operations Dashboard")
        
        # Calculate operational KPIs
        resolved_tickets = filtered_tickets[filtered_tickets['status'] == 'Resolved'].copy()
        resolved_tickets['resolution_hours'] = (
            (resolved_tickets['resolution_date'] - resolved_tickets['ticket_date']).dt.total_seconds() / 3600
        )
        
        sla_compliant = resolved_tickets[
            resolved_tickets['resolution_hours'] <= resolved_tickets['sla_target_hours']
        ].shape[0]
        sla_rate = (sla_compliant / len(resolved_tickets) * 100) if len(resolved_tickets) > 0 else 0
        
        ticket_backlog = filtered_tickets[
            filtered_tickets['status'].isin(['Open', 'In Progress', 'Escalated'])
        ].shape[0]
        
        avg_resolution = resolved_tickets['resolution_hours'].mean() if len(resolved_tickets) > 0 else 0
        total_outage_mins = filtered_outages['outage_duration_mins'].sum()
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("SLA Compliance Rate", f"{sla_rate:.1f}%")
        with col2:
            st.metric("Ticket Backlog", f"{ticket_backlog:,}")
        with col3:
            st.metric("Avg Resolution Time", f"{avg_resolution:.1f} hrs")
        with col4:
            st.metric("Total Outage Minutes", f"{total_outage_mins:,.0f}")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily Ticket Volume Trend
            
            # Add date filter controls for this specific chart
            st.markdown("**Filter by Date Range for this Chart:**")
            chart_date_range = st.date_input(
                "Select Date Range for Ticket Volume", 
                value=(filtered_tickets['ticket_date'].min().date(), filtered_tickets['ticket_date'].max().date()),
                min_value=filtered_tickets['ticket_date'].min().date(),
                max_value=filtered_tickets['ticket_date'].max().date(),
                key="chart_date_range"
            )
            
            # Filter data based on the chart-specific date range
            if len(chart_date_range) == 2:
                chart_start_date, chart_end_date = chart_date_range
                chart_filtered_tickets = filtered_tickets[
                    (filtered_tickets['ticket_date'] >= pd.to_datetime(chart_start_date)) & 
                    (filtered_tickets['ticket_date'] <= pd.to_datetime(chart_end_date))
                ]
            else:
                chart_filtered_tickets = filtered_tickets
            
            daily_tickets = chart_filtered_tickets.groupby('ticket_date').size().reset_index(name='count')
            
            fig1 = px.line(
                daily_tickets,
                x='ticket_date',
                y='count',
                title="Daily Ticket Volume Trend",
                labels={'ticket_date': 'Date', 'count': 'Tickets'}
            )
            fig1.update_traces(mode='lines+markers')
            
            # Add range selector buttons and date range selector for interactivity
            fig1.update_layout(
                xaxis=dict(
                    rangeslider=dict(visible=True),
                    type="date"
                )
            )
            
            fig1.add_annotation(text="Track ticket volume trends. Spikes may indicate service issues or system outages.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig1, width='stretch')
            
            # Insights for ticket volume
            if len(daily_tickets) > 0:
                avg_tickets = daily_tickets['count'].mean()
                st.caption(f"Average daily tickets: {avg_tickets:.0f}")
        
        with col2:
            # Ticket Backlog by Zone (Top 10)
            backlog_by_zone = filtered_tickets[
                filtered_tickets['status'].isin(['Open', 'In Progress', 'Escalated'])
            ].groupby('zone').size().sort_values(ascending=False).head(10)
            
            # Create a DataFrame for the backlog data
            backlog_df = pd.DataFrame({
                'tickets': backlog_by_zone.values,
                'zone': backlog_by_zone.index
            })
            
            fig2 = px.bar(
                backlog_df,
                x='tickets',
                y='zone',
                orientation='h',
                title="Ticket Backlog by Zone (Top 10)",
                labels={'x': 'Open Tickets', 'y': 'Zone'}
            )
            fig2.add_annotation(text="Identify zones with highest ticket backlogs requiring attention.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig2, width='stretch')
            
            # Insights for backlog
            if len(backlog_by_zone) > 0:
                top_zone = backlog_by_zone.index[0]
                top_zone_count = backlog_by_zone.iloc[0]
                st.caption(f"Zone with most backlog: {top_zone} ({top_zone_count} tickets)")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # SLA Compliance by Channel
            channel_sla = resolved_tickets.copy()
            channel_sla['sla_met'] = channel_sla['resolution_hours'] <= channel_sla['sla_target_hours']
            channel_stats = channel_sla.groupby('ticket_channel').agg({
                'sla_met': lambda x: (x.sum() / len(x) * 100)
            }).reset_index()
            channel_stats.columns = ['Channel', 'SLA Rate']
            
            fig3 = px.bar(
                channel_stats,
                x='Channel',
                y='SLA Rate',
                title="SLA Compliance by Channel",
                labels={'SLA Rate': 'SLA Compliance (%)'}
            )
            fig3.add_annotation(text="Evaluate performance across different support channels.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig3, width='stretch')
            
            # Insights for SLA compliance
            if len(channel_stats) > 0:
                lowest_channel = channel_stats.loc[channel_stats['SLA Rate'].idxmin(), 'Channel']
                lowest_rate = channel_stats['SLA Rate'].min()
                st.caption(f"Lowest SLA compliance: {lowest_channel} ({lowest_rate:.1f}%)")
        
        with col4:
            # Outage Minutes vs Ticket Count by Zone
            zone_outages = filtered_outages.groupby('zone')['outage_duration_mins'].sum().reset_index()
            zone_tickets = filtered_tickets.groupby('zone').size().reset_index(name='ticket_count')
            zone_corr = zone_outages.merge(zone_tickets, on='zone', how='outer').fillna(0)
            
            fig4 = px.scatter(
                zone_corr,
                x='outage_duration_mins',
                y='ticket_count',
                text='zone',
                title="Outage Minutes vs Ticket Count by Zone",
                labels={'outage_duration_mins': 'Outage Minutes', 'ticket_count': 'Tickets'}
            )
            fig4.update_traces(textposition='top center', marker=dict(size=12))
            fig4.add_annotation(text="Correlate network outages with ticket volume by zone.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig4, width='stretch')
            
            # Insights for outage correlation
            if len(zone_corr) > 0:
                max_outage_zone = zone_corr.loc[zone_corr['outage_duration_mins'].idxmax(), 'zone']
                st.caption(f"Zone with most outages: {max_outage_zone}")
        
        # Top Problem Zones Table
        st.markdown("### 📊 Top 10 Problem Zones")
        
        # Prepare data for analysis
        open_tickets = filtered_tickets[filtered_tickets['status'].isin(['Open', 'In Progress', 'Escalated'])].groupby('zone').size().reset_index(name='Open Tickets')
        
        # Calculate average resolution hours by zone
        if len(resolved_tickets) > 0 and 'resolution_hours' in resolved_tickets.columns:
            avg_resolution_by_zone = resolved_tickets.groupby('zone')['resolution_hours'].mean().reset_index(name='Avg Resolution Hours')
        else:
            # If no resolved tickets, set default value
            avg_resolution_by_zone = filtered_tickets.groupby('zone').size().reset_index()
            avg_resolution_by_zone['Avg Resolution Hours'] = 0  # Default to 0
        
        # Merge the data
        zone_analysis = open_tickets.merge(avg_resolution_by_zone, on='zone', how='left').fillna(0)
        zone_analysis.columns = ['Zone', 'Open Tickets', 'Avg Resolution Hours']
        
        zone_outage_mins = filtered_outages.groupby('zone')['outage_duration_mins'].sum().reset_index()
        zone_outage_mins.rename(columns={'zone': 'Zone'}, inplace=True)  # Rename to match
        zone_analysis = zone_analysis.merge(zone_outage_mins, on='Zone', how='left').fillna(0)
        
        # SLA breaches
        sla_breaches = resolved_tickets[
            resolved_tickets['resolution_hours'] > resolved_tickets['sla_target_hours']
        ].groupby('zone').size().reset_index(name='SLA Breach Count')
        sla_breaches.rename(columns={'zone': 'Zone'}, inplace=True)  # Rename to match
        zone_analysis = zone_analysis.merge(sla_breaches, on='Zone', how='left').fillna(0)
        
        zone_analysis = zone_analysis.sort_values('Open Tickets', ascending=False).head(10)
        zone_analysis['Avg Resolution Hours'] = zone_analysis['Avg Resolution Hours'].round(1)
        zone_analysis['outage_duration_mins'] = zone_analysis['outage_duration_mins'].round(0)
        zone_analysis['SLA Breach Count'] = zone_analysis['SLA Breach Count'].astype(int)
        
        st.dataframe(zone_analysis, use_container_width=True)
        
        # Service Tier Analysis
        st.markdown("### 🎯 Service Tier Performance")
                
        col1, col2 = st.columns(2)
                
        with col1:
            # Tier distribution
            tier_dist = filtered_subs['service_tier'].value_counts()
            fig_tier = px.pie(
                values=tier_dist.values,
                names=tier_dist.index,
                title="Service Tier Distribution"
            )
            fig_tier.add_annotation(text="Visualize the distribution of customers across service tiers.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig_tier, width='stretch')
                    
            # Insights for tier distribution
            if len(tier_dist) > 0:
                top_tier = tier_dist.index[0]
                st.caption(f"Largest tier: {top_tier}")
                
        with col2:
            # Ticket backlog by tier
            backlog_by_tier = filtered_tickets[
                filtered_tickets['status'].isin(['Open', 'In Progress', 'Escalated'])
            ].groupby('service_tier').size().reset_index(name='Backlog')
                    
            fig_tier_backlog = px.bar(
                backlog_by_tier,
                x='service_tier',
                y='Backlog',
                title="Ticket Backlog by Service Tier",
                labels={'service_tier': 'Service Tier'}
            )
            fig_tier_backlog.add_annotation(text="Compare ticket backlogs across service tiers.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
            st.plotly_chart(fig_tier_backlog, width='stretch')
                    
            # Insights for backlog by tier
            if len(backlog_by_tier) > 0:
                highest_backlog_tier = backlog_by_tier.loc[backlog_by_tier['Backlog'].idxmax(), 'service_tier']
                st.caption(f"Tier with most backlog: {highest_backlog_tier}")
                
        # SLA by tier
        tier_sla = resolved_tickets.copy()
        tier_sla['sla_met'] = tier_sla['resolution_hours'] <= tier_sla['sla_target_hours']
        tier_sla_stats = tier_sla.groupby('service_tier').agg({
            'sla_met': lambda x: (x.sum() / len(x) * 100)
        }).reset_index()
        tier_sla_stats.columns = ['Service Tier', 'SLA Rate']
                
        fig_tier_sla = px.bar(
            tier_sla_stats,
            x='Service Tier',
            y='SLA Rate',
            title="SLA Compliance Rate by Service Tier",
            labels={'SLA Rate': 'SLA Compliance (%)'}
        )
        fig_tier_sla.add_annotation(text="Evaluate SLA compliance across different service tiers.", 
                               xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, 
                               font=dict(size=10, color="white"), bgcolor="gray")
        st.plotly_chart(fig_tier_sla, width='stretch')
                
        # Insights for SLA by tier
        if len(tier_sla_stats) > 0:
            lowest_sla_tier = tier_sla_stats.loc[tier_sla_stats['SLA Rate'].idxmin(), 'Service Tier']
            lowest_sla_rate = tier_sla_stats['SLA Rate'].min()
            st.caption(f"Tier with lowest SLA: {lowest_sla_tier} ({lowest_sla_rate:.1f}%)")

if __name__ == "__main__":
    main()
