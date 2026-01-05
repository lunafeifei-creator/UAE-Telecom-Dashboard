import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Date ranges
end_date = datetime(2026, 1, 4)
start_date = end_date - timedelta(days=119)
activation_start = end_date - timedelta(days=730)

# Configuration
SUBSCRIBERS_COUNT = 5000
USAGE_COUNT = 50000
BILLING_COUNT = 15000
TICKETS_COUNT = 6000
OUTAGES_COUNT = 200

# Categories
CITIES = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Fujairah']
CITY_DIST = [0.35, 0.30, 0.20, 0.10, 0.05]
ZONES = [f'Zone {i}' for i in range(1, 9)]
PLAN_TYPES = ['Prepaid', 'Postpaid']
PLAN_NAMES = ['Basic', 'Standard', 'Premium', 'Unlimited']
STATUSES = ['Active', 'Suspended', 'Churned']
PAYMENT_STATUSES = ['Paid', 'Overdue', 'Partial', 'Pending']
TICKET_CATEGORIES = ['Network Issue', 'Billing Query', 'Technical Support', 'Plan Change', 'Complaint']
TICKET_STATUSES = ['Resolved', 'In Progress', 'Open', 'Escalated']
TICKET_CHANNELS = ['Call Center', 'App', 'Online Chat', 'Retail Store']
PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
TEAMS = ['Tier 1', 'Tier 2', 'Tier 3', 'Field Ops']
OUTAGE_TYPES = ['Planned Maintenance', 'Equipment Failure', 'Power Outage', 'Fiber Cut', 'Weather']

print("Generating SUBSCRIBERS table...")
subscribers_data = []
for i in range(SUBSCRIBERS_COUNT):
    sub_id = f"SUB_{str(i+1).zfill(5)}"
    city = np.random.choice(CITIES, p=CITY_DIST)
    zone = np.random.choice(ZONES)
    plan_type = np.random.choice(['Prepaid', 'Postpaid'], p=[0.6, 0.4])
    
    if plan_type == 'Prepaid':
        plan_name = np.random.choice(['Basic', 'Standard'], p=[0.5, 0.5])
        monthly_charge = np.random.uniform(50, 150)
    else:
        plan_name = np.random.choice(['Standard', 'Premium', 'Unlimited'], p=[0.4, 0.4, 0.2])
        if plan_name == 'Standard':
            monthly_charge = np.random.uniform(100, 200)
        elif plan_name == 'Premium':
            monthly_charge = np.random.uniform(200, 350)
        else:
            monthly_charge = np.random.uniform(350, 500)
    
    activation_date = activation_start + timedelta(days=random.randint(0, 730))
    status = np.random.choice(['Active', 'Suspended', 'Churned'], p=[0.85, 0.10, 0.05])
    
    subscribers_data.append({
        'subscriber_id': sub_id,
        'subscriber_name': f'Customer {i+1}',
        'city': city,
        'zone': zone,
        'plan_type': plan_type,
        'plan_name': plan_name,
        'monthly_charge': round(monthly_charge, 2),
        'activation_date': activation_date.date(),
        'status': status
    })

subscribers_df = pd.DataFrame(subscribers_data)

# Inject duplicates (80 records)
dup_indices = np.random.choice(subscribers_df.index, 80, replace=False)
duplicates = subscribers_df.loc[dup_indices].copy()
subscribers_df = pd.concat([subscribers_df, duplicates], ignore_index=True)

# Inject inconsistent labels
inconsistent_indices = np.random.choice(subscribers_df.index, 200, replace=False)
for idx in inconsistent_indices[:50]:
    subscribers_df.at[idx, 'plan_type'] = np.random.choice(['PREPAID', 'prepaid', 'Pre-paid'])
for idx in inconsistent_indices[50:100]:
    subscribers_df.at[idx, 'city'] = subscribers_df.at[idx, 'city'].replace(' ', '').replace('Abu Dhabi', 'AbuDhabi')
for idx in inconsistent_indices[100:150]:
    if subscribers_df.at[idx, 'city'] == 'Abu Dhabi':
        subscribers_df.at[idx, 'city'] = np.random.choice(['AbuDhabi', 'Abu-Dhabi', 'AD'])

print(f"Generated {len(subscribers_df)} subscriber records (including duplicates)")

print("Generating USAGE_RECORDS table...")
active_subs = subscribers_df[subscribers_df['status'] == 'Active']['subscriber_id'].unique()
usage_data = []
for i in range(USAGE_COUNT):
    sub_id = np.random.choice(active_subs)
    usage_date = start_date + timedelta(days=random.randint(0, 119))
    
    usage_data.append({
        'usage_id': f"USG_{str(i+1).zfill(6)}",
        'subscriber_id': sub_id,
        'usage_date': usage_date.date(),
        'data_usage_gb': round(np.random.gamma(2, 5), 2),
        'voice_minutes': random.randint(0, 500),
        'sms_count': random.randint(0, 100),
        'roaming_charges': round(np.random.exponential(20), 2),
        'addon_charges': round(np.random.exponential(15), 2)
    })

usage_df = pd.DataFrame(usage_data)

# Inject missing values (500 records)
missing_indices = np.random.choice(usage_df.index, 500, replace=False)
usage_df.loc[missing_indices, 'data_usage_gb'] = np.nan

# Inject outliers (30 records with data > 500 GB)
outlier_indices = np.random.choice(usage_df.index, 30, replace=False)
usage_df.loc[outlier_indices, 'data_usage_gb'] = np.random.uniform(500, 1000)

# Inject impossible values (10 records with usage before activation)
impossible_indices = np.random.choice(usage_df.index, 10, replace=False)
for idx in impossible_indices:
    sub_id = usage_df.at[idx, 'subscriber_id']
    activation = subscribers_df[subscribers_df['subscriber_id'] == sub_id]['activation_date'].values[0]
    usage_df.at[idx, 'usage_date'] = pd.to_datetime(activation) - timedelta(days=random.randint(1, 30))

print(f"Generated {len(usage_df)} usage records")

print("Generating BILLING table...")
billing_data = []
billing_months = pd.date_range(start=start_date, end=end_date, freq='MS')[:3]

for sub_id in subscribers_df['subscriber_id'].unique()[:BILLING_COUNT//3]:
    sub_info = subscribers_df[subscribers_df['subscriber_id'] == sub_id].iloc[0]
    
    for month in billing_months:
        bill_amount = sub_info['monthly_charge'] + np.random.uniform(0, 50)
        payment_status = np.random.choice(PAYMENT_STATUSES, p=[0.7, 0.15, 0.10, 0.05])
        
        payment_date = None
        if payment_status == 'Paid':
            payment_date = month + timedelta(days=random.randint(1, 30))
        
        credit_adj = 0
        adj_reason = None
        if random.random() < 0.1:
            credit_adj = round(np.random.uniform(10, 100), 2)
            adj_reason = np.random.choice(['Network Issue', 'Billing Error', 'Goodwill', 'Promo Credit'])
        
        billing_data.append({
            'bill_id': f"BILL_{len(billing_data)+1:06d}",
            'subscriber_id': sub_id,
            'billing_month': month.date(),
            'bill_amount': round(bill_amount, 2),
            'payment_status': payment_status,
            'payment_date': payment_date.date() if payment_date else None,
            'credit_adjustment': credit_adj,
            'adjustment_reason': adj_reason
        })

billing_df = pd.DataFrame(billing_data)

# Inject duplicates (40 records)
dup_indices = np.random.choice(billing_df.index, 40, replace=False)
duplicates = billing_df.loc[dup_indices].copy()
billing_df = pd.concat([billing_df, duplicates], ignore_index=True)

# Inject missing payment_date for Paid status (200 records)
paid_indices = billing_df[billing_df['payment_status'] == 'Paid'].index
missing_payment_indices = np.random.choice(paid_indices, min(200, len(paid_indices)), replace=False)
billing_df.loc[missing_payment_indices, 'payment_date'] = None

# Inject negative bill amounts (5 records)
negative_indices = np.random.choice(billing_df.index, 5, replace=False)
billing_df.loc[negative_indices, 'bill_amount'] = -np.random.uniform(10, 100)

# Inject outliers (20 bills > 5000 AED)
outlier_indices = np.random.choice(billing_df.index, 20, replace=False)
billing_df.loc[outlier_indices, 'bill_amount'] = np.random.uniform(5000, 10000)

print(f"Generated {len(billing_df)} billing records")

print("Generating NETWORK_OUTAGES table...")
outages_data = []
for i in range(OUTAGES_COUNT):
    city = np.random.choice(CITIES, p=CITY_DIST)
    zone = np.random.choice(ZONES)
    outage_date = start_date + timedelta(days=random.randint(0, 119))
    
    start_hour = random.randint(0, 23)
    start_time = outage_date.replace(hour=start_hour, minute=random.randint(0, 59))
    duration_mins = random.randint(15, 480)
    end_time = start_time + timedelta(minutes=duration_mins)
    
    outages_data.append({
        'outage_id': f"OUT_{str(i+1).zfill(4)}",
        'zone': zone,
        'city': city,
        'outage_date': outage_date.date(),
        'outage_start_time': start_time,
        'outage_end_time': end_time,
        'outage_duration_mins': duration_mins,
        'outage_type': np.random.choice(OUTAGE_TYPES, p=[0.25, 0.35, 0.20, 0.15, 0.05]),
        'affected_subscribers': random.randint(50, 5000)
    })

outages_df = pd.DataFrame(outages_data)

# Inject missing duration (10 records)
missing_indices = np.random.choice(outages_df.index, 10, replace=False)
outages_df.loc[missing_indices, 'outage_duration_mins'] = np.nan

# Inject outliers (10 outages > 1440 mins)
outlier_indices = np.random.choice(outages_df.index, 10, replace=False)
outages_df.loc[outlier_indices, 'outage_duration_mins'] = np.random.randint(1441, 3000)

print(f"Generated {len(outages_df)} outage records")

print("Generating TICKETS table...")
tickets_data = []
for i in range(TICKETS_COUNT):
    sub_id = np.random.choice(subscribers_df['subscriber_id'].unique())
    sub_info = subscribers_df[subscribers_df['subscriber_id'] == sub_id].iloc[0]
    
    ticket_date = start_date + timedelta(days=random.randint(0, 119))
    category = np.random.choice(TICKET_CATEGORIES, p=[0.35, 0.25, 0.20, 0.12, 0.08])
    status = np.random.choice(TICKET_STATUSES, p=[0.65, 0.20, 0.10, 0.05])
    
    resolution_date = None
    if status == 'Resolved':
        resolution_hours = random.randint(1, 120)
        resolution_date = ticket_date + timedelta(hours=resolution_hours)
    
    sla_target = np.random.choice([24, 48, 72], p=[0.3, 0.5, 0.2])
    
    tickets_data.append({
        'ticket_id': f"TKT_{str(i+1).zfill(6)}",
        'subscriber_id': sub_id,
        'ticket_date': ticket_date.date(),
        'ticket_channel': np.random.choice(TICKET_CHANNELS, p=[0.4, 0.3, 0.2, 0.1]),
        'ticket_category': category,
        'priority': np.random.choice(PRIORITIES, p=[0.3, 0.4, 0.2, 0.1]),
        'status': status,
        'resolution_date': resolution_date.date() if resolution_date else None,
        'sla_target_hours': sla_target,
        'assigned_team': np.random.choice(TEAMS, p=[0.4, 0.3, 0.2, 0.1])
    })

tickets_df = pd.DataFrame(tickets_data)

# Link some tickets to zones from subscribers
tickets_df = tickets_df.merge(
    subscribers_df[['subscriber_id', 'zone', 'city']].drop_duplicates('subscriber_id'),
    on='subscriber_id',
    how='left'
)

# Inject duplicates (60 records)
dup_indices = np.random.choice(tickets_df.index, 60, replace=False)
duplicates = tickets_df.loc[dup_indices].copy()
tickets_df = pd.concat([tickets_df, duplicates], ignore_index=True)

# Inject missing resolution_date for Resolved (100 records)
resolved_indices = tickets_df[tickets_df['status'] == 'Resolved'].index
missing_resolution = np.random.choice(resolved_indices, min(100, len(resolved_indices)), replace=False)
tickets_df.loc[missing_resolution, 'resolution_date'] = None

# Inject inconsistent status labels
status_indices = np.random.choice(tickets_df.index, 150, replace=False)
for idx in status_indices:
    if tickets_df.at[idx, 'status'] == 'Resolved':
        tickets_df.at[idx, 'status'] = np.random.choice(['resolved', 'RESOLVED', 'Closed'])

# Inject impossible values (15 records with resolution < ticket date)
impossible_indices = np.random.choice(
    tickets_df[tickets_df['resolution_date'].notna()].index, 15, replace=False
)
for idx in impossible_indices:
    ticket_date = pd.to_datetime(tickets_df.at[idx, 'ticket_date'])
    tickets_df.at[idx, 'resolution_date'] = ticket_date - timedelta(days=random.randint(1, 10))

print(f"Generated {len(tickets_df)} ticket records")

# Save to CSV
print("\nSaving CSV files...")
subscribers_df.to_csv('subscribers.csv', index=False)
usage_df.to_csv('usage_records.csv', index=False)
billing_df.to_csv('billing.csv', index=False)
tickets_df.to_csv('tickets.csv', index=False)
outages_df.to_csv('network_outages.csv', index=False)

print("\n✓ All CSV files generated successfully!")
print("\nData Quality Issues Injected:")
print("- Duplicates: Subscribers (80), Billing (40), Tickets (60)")
print("- Missing Values: Usage (500), Billing payment_date (200), Tickets resolution_date (100), Outages duration (10)")
print("- Inconsistent Labels: Plan types, Cities, Ticket status")
print("- Outliers: Usage data (30), Bills (20), Outages (10)")
print("- Impossible Values: Usage dates (10), Ticket dates (15), Bills (5 negative)")
