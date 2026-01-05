# UAE Telecom Revenue & Service Operations Dashboard

## 📋 Business Context

**ConnectUAE** is a telecommunications provider serving 500,000+ subscribers across the UAE (Dubai, Abu Dhabi, Sharjah, Ajman, Fujairah). The company offers prepaid and postpaid mobile plans, international roaming, data add-ons, and home broadband services.

### Business Challenge
ConnectUAE faces:
- Declining ARPU in certain segments
- Rising complaint volumes
- Network outages impacting customer satisfaction
- Lack of integrated view of revenue health and service operations

### Solution
A dual-view Streamlit dashboard providing:
- **Executive View**: Revenue tracking, ARPU trends, retention metrics, billing health
- **Manager View**: Ticket analytics, SLA compliance, network outage correlation, service tier performance

---

## 🎯 Business Objectives

1. **Revenue Tracking**: Monitor total revenue, ARPU, and revenue mix by plan type and city
2. **Subscriber Health**: Track active subscribers and retention ratios
3. **Billing & Collections**: Identify overdue payments and revenue at risk
4. **Service Quality**: Measure ticket volumes, resolution times, and SLA compliance
5. **Network Stability**: Track outages and their impact on complaints
6. **Credit Monitoring**: Quantify adjustments and identify patterns

---

## 📊 Data Model

### Tables and Relationships
```
SUBSCRIBERS (1) ──────< (M) USAGE_RECORDS
    │
    │ (1)
    ▼
BILLING (M)
    │
    │ (1)
    ▼
TICKETS (M) ──────> (M:1) NETWORK_OUTAGES (linked by zone + date)
```

### Tables
1. **SUBSCRIBERS** (5,000 records): Subscriber demographics, plan details, activation dates
2. **USAGE_RECORDS** (50,000 records): Data, voice, SMS usage, roaming and add-on charges
3. **BILLING** (15,000 records): Monthly bills, payment status, credit adjustments
4. **TICKETS** (6,000 records): Support tickets, channels, categories, resolution tracking
5. **NETWORK_OUTAGES** (200 records): Outage incidents, durations, affected zones

---

## 🔧 Data Quality Issues & Cleaning Steps

### Issues Injected
1. **Duplicates**: 80 subscribers, 40 bills, 60 tickets
2. **Missing Values**: 500 usage records, 200 billing payment dates, 100 ticket resolutions
3. **Inconsistent Labels**: Plan types ("Prepaid", "PREPAID", "Pre-paid"), cities ("Abu Dhabi", "AbuDhabi", "AD")
4. **Outliers**: 30 usage records >500GB, 20 bills >AED 5,000, 10 outages >24 hours
5. **Impossible Values**: 15 tickets with resolution before creation, 10 usage before activation, 5 negative bills

### Cleaning Process
1. ✅ Remove duplicates based on primary keys (subscriber_id, bill_id, ticket_id)
2. ✅ Standardize plan types, cities, and ticket status labels
3. ✅ Impute missing data_usage_gb with subscriber average or 0
4. ✅ Cap outliers: data usage >100GB, bills >AED 2,000
5. ✅ Remove records with impossible date sequences
6. ✅ Remove negative bill amounts
7. ✅ Calculate missing outage durations from timestamps

---

## 📈 KPI Dictionary

### Executive KPIs
| KPI | Definition | Formula |
|-----|------------|---------|
| Total Revenue | Total billed revenue in period | Sum of bill_amount |
| ARPU | Average revenue per active subscriber | Total Revenue ÷ Active Subscribers |
| Retention Ratio | Percentage of subscribers remaining active | (Active Subscribers ÷ Total Subscribers) × 100 |
| Overdue Revenue | Revenue at risk from unpaid bills | Sum of bill_amount where payment_status = 'Overdue' |
| Revenue by City | Revenue contribution by city | (City Revenue ÷ Total Revenue) × 100 |
| Prepaid vs Postpaid Mix | Revenue share by plan type | (Plan Type Revenue ÷ Total Revenue) × 100 |
| Credit Adjustment Total | Total credits/adjustments issued | Sum of credit_adjustment |

### Manager/Operational KPIs
| KPI | Definition | Formula |
|-----|------------|---------|
| Ticket Volume | Total tickets opened in period | Count of all tickets |
| SLA Compliance Rate | % tickets resolved within SLA | (Tickets within SLA ÷ Total Resolved) × 100 |
| Avg Resolution Time | Mean time to resolve tickets | Sum of resolution hours ÷ Resolved Tickets |
| Ticket Backlog | Unresolved tickets | Count of Open/In Progress/Escalated |
| Escalation Rate | % tickets escalated | (Escalated Tickets ÷ Total Tickets) × 100 |
| Total Outage Minutes | Sum of all outage durations | Sum of outage_duration_mins |
| Network Issue Ratio | % tickets related to network | (Network Tickets ÷ Total Tickets) × 100 |

---

## 🎯 Service Tier Classification (Primary Feature)

Rule-based priority tier system:

- **Priority 1 (Critical)**: Postpaid Unlimited plans OR tenure >3 years
- **Priority 2 (High)**: Postpaid Premium plans OR tenure >1 year
- **Priority 3 (Standard)**: All other Postpaid subscribers
- **Priority 4 (Basic)**: All Prepaid subscribers

Dashboard displays:
- Tier distribution pie chart
- Ticket backlog by tier
- SLA compliance rate by tier

---

## 🚀 Installation & Usage

### Prerequisites
```bash
Python 3.8+
pip install streamlit pandas numpy plotly
```

### Step 1: Generate Data
```bash
python data_generator.py
```

This creates 5 CSV files:
- subscribers.csv
- usage_records.csv
- billing.csv
- tickets.csv
- network_outages.csv

### Step 2: Launch Dashboard
```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

---

## 📱 Dashboard Features

### Sidebar Filters (6 filters)
1. **Date Range Picker**: Filter by date range
2. **City Multi-Select**: Dubai, Abu Dhabi, Sharjah, Ajman, Fujairah
3. **Plan Type**: Prepaid, Postpaid
4. **Plan Name**: Basic, Standard, Premium, Unlimited
5. **Ticket Category**: Network Issue, Billing Query, Technical Support, Plan Change, Complaint
6. **Subscriber Status**: Active, Suspended, Churned

### View Toggle
Radio button to switch between Executive and Manager views

### Executive View
**KPI Cards (4)**:
- Total Revenue (AED)
- ARPU (AED)
- Retention Ratio (%)
- Overdue Revenue (AED)

**Charts (4)**:
1. Line Chart: Monthly ARPU Trend
2. Stacked Bar Chart: Revenue by Plan Type (Monthly)
3. Horizontal Bar Chart: Revenue by City
4. Pie Chart: Payment Status Distribution

**Insights Box**: Auto-generated business insights

### Manager View
**KPI Cards (4)**:
- SLA Compliance Rate (%)
- Ticket Backlog (Count)
- Average Resolution Time (Hours)
- Total Outage Minutes

**Charts (4)**:
1. Line Chart: Daily Ticket Volume Trend
2. Bar Chart: Ticket Backlog by Zone (Top 10)
3. Bar Chart: SLA Compliance by Channel
4. Scatter Chart: Outage Minutes vs Ticket Count by Zone

**Table**: Top 10 Problem Zones (sortable)

**Service Tier Analysis (3 charts)**:
- Tier distribution pie chart
- Ticket backlog by tier
- SLA compliance by tier

---

## 🎓 Key Business Questions Answered

### Executive Questions
1. ✅ What is our ARPU trend by month? Which plan type drives most revenue?
2. ✅ Which city has highest revenue and most overdue payments?
3. ✅ What is our retention ratio? Are we losing subscribers?
4. ✅ How much revenue is at risk from overdue accounts?
5. ✅ What is the total credit adjustment issued?

### Manager Questions
1. ✅ What is the current ticket backlog by zone?
2. ✅ What is our SLA compliance rate by channel?
3. ✅ Is there correlation between outages and ticket spikes?
4. ✅ What are top ticket categories and resolution times?
5. ✅ Which support team has longest resolution time?

---

## 📁 Project Structure

```
project/
│
├── data_generator.py      # Generates synthetic data with quality issues
├── app.py                 # Main Streamlit dashboard application
├── README.md              # This file
├── requirements.txt       # Python dependencies
│
└── [Generated CSV files]
    ├── subscribers.csv
    ├── usage_records.csv
    ├── billing.csv
    ├── tickets.csv
    └── network_outages.csv
```

---

## 🔍 Assumptions & Design Decisions

1. **Date Range**: Last 120 days (Sep 7, 2025 to Jan 4, 2026)
2. **Retention Ratio**: Simplified as (Active Subscribers ÷ Total Subscribers) × 100
3. **Service Tier**: Calculated based on plan type and tenure at load time
4. **Data Cleaning**: Performed automatically on data load with caching
5. **Currency**: All amounts in AED (UAE Dirham)
6. **SLA Targets**: 24, 48, or 72 hours depending on ticket priority
7. **Missing Resolutions**: Tickets without resolution dates are excluded from time calculations

---

## 📊 Sample Insights Generated

**Executive View Example**:
> "ARPU is AED 245.50, with 62.3% from Postpaid plans. Retention ratio is 85.0%. AED 125,000 is at risk from overdue accounts in Dubai."

**Manager View Focus**:
- Identifies zones with highest ticket backlogs
- Correlates network outages with complaint spikes
- Tracks SLA performance across support channels
- Prioritizes service improvements by tier

---

## 🏆 Project Highlights

✅ **Complete Data Pipeline**: Synthetic data generation with realistic relationships and quality issues  
✅ **Comprehensive Cleaning**: 7-step data quality process  
✅ **14 KPIs**: All business metrics calculated accurately  
✅ **Dual Views**: Executive and operational perspectives  
✅ **6 Interactive Filters**: Dynamic data exploration  
✅ **Service Tier Classification**: Rule-based prioritization system  
✅ **Visual Analytics**: 11 charts using Plotly  
✅ **Actionable Insights**: Auto-generated business recommendations

---

## 📞 Support

For questions about the dashboard or data model, refer to the inline documentation in the code files.

**Project**: UAE Telecom Dashboard  
**Company**: ConnectUAE  
**Version**: 1.0  
**Last Updated**: January 2026
