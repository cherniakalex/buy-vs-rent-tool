# buy_vs_rent_tool_v13.py
# Full version: Scenarios A, B, C + Inflation + Tax + Cash Flow + Drop-downs + Detailed Summary + Scenario C mortgage recalculation

import os
import time
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.markdown("""
    <style>
    .big-font {
        font-size:24px !important;
    }
    .metric-label > div {
        font-size: 22px !important;
    }
    .metric-value > div {
        font-size: 28px !important;
        font-weight: bold !important;
    }
    /* Additional styling for input labels and input boxes */
    section[data-testid="stSidebar"] label,
    label[data-testid="stWidgetLabel"] {
        font-size: 22px !important;
        font-weight: 600 !important;
    }
    .stNumberInput input,
    .stTextInput input,
    .stSlider,
    .stSelectbox,
    .stDateInput {
        font-size: 22px !important;
    }
    .st-expanderContent,
    .st-expanderHeader {
        font-size: 22px !important;
    }
    </style>
""", unsafe_allow_html=True)


last_modified = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(__file__)))
st.title(f"🏠 Buy vs Rent Decision Tool ({last_modified})")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.header("Parameters")

    available_capital = st.number_input("Available Capital (₪)", value=1_101_111, step=10_000)
    apartment_price = st.number_input("Scenario A - New Apartment Price (₪)", value=4_000_000, step=100_000)
    apartment_price_c = st.number_input("Scenario C - New Apartment Price (₪)", value=4_700_000, step=100_000)
    existing_apartment_value = st.number_input("Existing Apartment Value (₪)", value=3_200_000, step=100_000)

    rent_per_month = st.number_input("Monthly Rent (₪)", value=3_500, step=500)
    rent_years = st.slider("Years of Paying Rent (Scenario B)", 1, 30, 3)

    improvement_monthly = st.number_input("Monthly Improvement Cost (₪)", value=3_500, step=500)
    improvement_years = st.slider("Improvement Duration (Years)", 1, 10, 3)

    existing_mortgage_monthly = st.number_input("Monthly Mortgage (Existing Apartment) (₪)", value=3_500, step=500)
    existing_mortgage_years = st.slider("Mortgage Duration (Existing Apartment)", 1, 30, 8)

    loan_term_years = st.slider("Loan Term for New Mortgage (Years)", 5, 40, 30)
    mortgage_interest_annual = st.slider("Mortgage Interest (%)", 1.0, 10.0, 4.5) / 100
    investment_return_annual = st.slider("Investment Return (%)", 1.0, 12.0, 8.0) / 100
    appreciation_rate_annual = st.slider("Apartment Appreciation (%)", 0.0, 10.0, 4.5) / 100
    inflation_rate_annual = st.slider("Inflation Rate (%)", 0.0, 5.0, 2.0) / 100
    rental_income_monthly = st.number_input("Rental Income of the Existing Apartment (from Year 4) (₪)", value=7_000, step=500)
    bonus_income_monthly = st.number_input("Temporary Bonus Income (First 3 Years) (₪)", value=6_500, step=500)
    rental_income_tax_rate = st.slider("Rental Income Tax (%)", 0.0, 50.0, 5.0) / 100

# Setup calculations
months = loan_term_years * 12
monthly_interest = (1 + mortgage_interest_annual)**(1/12) - 1
monthly_investment_return = (1 + investment_return_annual)**(1/12) - 1
monthly_appreciation = (1 + appreciation_rate_annual)**(1/12) - 1
monthly_inflation = (1 + inflation_rate_annual)**(1/12) - 1

start_date = datetime(2026, 1, 1)
dates = [start_date + timedelta(days=30 * i) for i in range(months)]

# Filter for 5-year ticks
year_ticks = [date for i, date in enumerate(dates) if (start_date.year + i // 12) % 5 == 0 and i % 12 == 0]

# SCENARIO FUNCTIONS

def scenario_a():
    capital = available_capital
    price = apartment_price
    mortgage = price - capital
    payment = (mortgage * monthly_interest) / (1 - (1 + monthly_interest) ** -months)
    value = price
    total_rental_income = 0
    cashflow = []
    total_paid = 0
    value_history = []

    for m in range(months):
        value *= 1 + monthly_appreciation
        value_history.append(value)
        total_paid += existing_mortgage_monthly + payment
        cashflow.append(-existing_mortgage_monthly - payment)

        if m >= 36:
            rent_income = rental_income_monthly * (1 - rental_income_tax_rate)
            total_rental_income += rent_income
            cashflow[-1] += rent_income

        if m < 36:
            cashflow[-1] += bonus_income_monthly

    return {
        "total_paid": total_paid,
        "final_assets": value,
        "net_gain": value + total_rental_income + bonus_income_monthly * 36 - total_paid,
        "cashflow": cashflow,
        "value_history": value_history,
    }


def scenario_b():
    investment = available_capital
    total_paid = 0
    cashflow = []
    value_history = []

    for m in range(months):
        investment *= 1 + monthly_investment_return
        value_history.append(investment)
        improve = improvement_monthly if m < improvement_years * 12 else 0
        mortgage_pay = existing_mortgage_monthly if m < existing_mortgage_years * 12 else 0
        bonus_income = bonus_income_monthly if m < 36 else 0

        total_paid += improve + mortgage_pay - bonus_income
        cashflow.append(-improve - mortgage_pay + bonus_income)

    return {
        "total_paid": total_paid,
        "final_assets": investment,
        "net_gain": investment - total_paid,
        "cashflow": cashflow,
        "value_history": value_history,
    }

def scenario_c():
    capital = available_capital
    price = apartment_price_c
    mortgage = price - capital
    months_total = months
    payment_full = (mortgage * monthly_interest) / (1 - (1 + monthly_interest) ** -months_total)
    value = price
    total_paid = 0
    value_history = []
    cashflow = []

    for m in range(months):
        value *= 1 + monthly_appreciation
        value_history.append(value)

        if m < 36:
            total_paid += existing_mortgage_monthly + payment_full
            cashflow.append(-existing_mortgage_monthly - payment_full + bonus_income_monthly)

        elif m == 36:
            # Correct amortization calculation for remaining principal
            remaining_principal = mortgage * ((1 + monthly_interest) ** months_total - (1 + monthly_interest) ** m) / ((1 + monthly_interest) ** months_total - 1)
            new_balance = remaining_principal - existing_apartment_value
            new_balance = max(new_balance, 0)  # Prevent negative mortgage
            remaining_months = months_total - m
            payment_reduced = (new_balance * monthly_interest) / (1 - (1 + monthly_interest) ** -remaining_months)
            total_paid += payment_reduced
            cashflow.append(-payment_reduced)

        else:
            total_paid += payment_reduced
            cashflow.append(-payment_reduced)

    return {
        "total_paid": total_paid,
        "final_assets": value,
        "net_gain": value + bonus_income_monthly * 36 - total_paid,
        "cashflow": cashflow,
        "value_history": value_history,
        "payment_full": payment_full,
        "payment_reduced": payment_reduced,
        "remaining_months": remaining_months,
    }

a = scenario_a()
b = scenario_b()
c = scenario_c()

# SUMMARY
with col2:
    st.header("Summary")

    with st.expander("🟦 Scenario A: Buy New with Capital + Rent Existing"):
        st.metric("Total Paid", f"₪{a['total_paid']:,.0f}")
        with st.expander("🔍 Breakdown: Total Paid"):
            st.markdown(f"- Existing Mortgage: ₪{existing_mortgage_monthly} × {existing_mortgage_years * 12} months")
            st.markdown(f"- New Mortgage Payment: based on loan of ₪{apartment_price - available_capital:,.0f}")
        st.metric("Final Asset Value", f"₪{a['final_assets']:,.0f}")
        with st.expander("🔍 Breakdown: Final Assets"):
            st.markdown(f"- Appreciated Value of New Apartment over {months//12} years")
            st.markdown(f"- Rental Income: ₪{rental_income_monthly * (1 - rental_income_tax_rate):,.0f} × {months - 36} months")
            st.markdown(f"- Bonus Income: ₪{bonus_income_monthly:,.0f} × 36 months")
        st.metric("Net Gain", f"₪{a['net_gain']:,.0f}")

    with st.expander("🟩 Scenario B: Rent for living + Invest"):
        st.metric("Total Paid", f"₪{b['total_paid']:,.0f}")
        with st.expander("🔍 Breakdown: Total Paid"):
            st.markdown(f"- Improvements: ₪{improvement_monthly:,.0f} × {improvement_years * 12} months")
            st.markdown(f"- Existing Mortgage: ₪{existing_mortgage_monthly:,.0f} × {existing_mortgage_years * 12} months")
            st.markdown(f"- Bonus Income Offset: ₪{bonus_income_monthly:,.0f} × 36 months")
        st.metric("Final Asset Value", f"₪{b['final_assets']:,.0f}")
        with st.expander("🔍 Breakdown: Final Assets"):
            st.markdown(f"- Investment Return on ₪{available_capital:,.0f} over {months//12} years")
        st.metric("Net Gain", f"₪{b['net_gain']:,.0f}")

    with st.expander("🟨 Scenario C: Buy New with Capital + Sell Existing after 3 years"):
        st.metric("Total Paid", f"₪{c['total_paid']:,.0f}")
        with st.expander("🔍 Breakdown: Total Paid"):
            st.markdown(f"- Existing Mortgage: ₪{existing_mortgage_monthly:,.0f} × 36 months")
            with st.expander("Monthly Payments: New Mortgage until sale (months 0–35)"):
                st.markdown(f"- Monthly Payment: ₪{c['payment_full']:,.0f}")
            with st.expander("Monthly Payments: New Mortgage post-sale (from month 36)"):
                st.markdown(f"- Monthly Payment: ₪{c['payment_reduced']:,.0f} × {c['remaining_months']} months")
            st.markdown(f"- Bonus Income: ₪{bonus_income_monthly:,.0f} × 36 months (offsets total payments)")
        st.metric("Final Asset Value", f"₪{c['final_assets']:,.0f}")
        with st.expander("🔍 Breakdown: Final Assets"):
            st.markdown(f"- Appreciated Value of New Apartment over {months//12} years")
            st.markdown(f"- Bonus Income: ₪{bonus_income_monthly:,.0f} × 36 months")
        st.metric("Net Gain", f"₪{c['net_gain']:,.0f}")

# CHARTS
with col3:
    st.header("📈 Final Asset Value Over Time")
    fig, ax = plt.subplots()
    ax.plot(dates, a['value_history'], label="Scenario A", color="blue")
    ax.plot(dates, b['value_history'], label="Scenario B", color="green")
    ax.plot(dates, c['value_history'], label="Scenario C", color="yellow")
    ax.set_xlabel("Date")
    ax.set_ylabel("₪ Value")
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"₪{x:,.0f}"))
    ax.set_xticks(year_ticks)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    fig.autofmt_xdate()
    st.pyplot(fig)

    st.header("📉 Monthly Cash Flow")
    fig2, ax2 = plt.subplots()
    ax2.plot(dates, a['cashflow'], label="Scenario A", color="blue")
    ax2.plot(dates, b['cashflow'], label="Scenario B", color="green")
    ax2.plot(dates, c['cashflow'], label="Scenario C", color="yellow")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("₪ Cash Flow")
    ax2.legend()
    ax2.axhline(0, color='gray', linestyle='--')
    ax2.set_xticks(year_ticks)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    fig2.autofmt_xdate()
    st.pyplot(fig2)
