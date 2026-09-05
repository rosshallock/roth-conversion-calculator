
#=====================================================================
#ROTH CONVERSION CALCULATOR & ESTATE OPTIMIZATION ENGINE
#=====================================================================
"""
Purpose:
  Simulates a 28-year financial timeline (from 2027 to 2054) to 
  determine the optimal multi-year Roth conversion schedule. 
  
Strategy & Methodology:
  - Generates a 23-year active conversion stream (terminating at age 75 
    to completely avoid overlapping with Required Minimum Distributions).
  - Uses a 10,000-run random simulation loop to benchmark various 
    annual conversion strategies against a baseline "Zero Conversion" plan.
  - Automatically incorporates progressive IRS tax brackets, 
    inflation adjustments, and Social Security income inclusion rules.
  - Values the final estate by discounting the Traditional IRA balance 
    by an expected heir tax drag factor (default: 23% / 0.77 factor) 
    to facilitate an accurate comparison against Roth assets.
"""

import random

# --- FEDERAL TAX LIABILITY FUNCTION ---
def calculate_federal_tax(ordinary_income, qualified_dividends, target_year, inflation_factor):
    """
    Computes total federal tax liability for a Single filer taking the standard deduction.
    
    Inputs:
    - ordinary_income: Total gross ordinary income ($)
    - qualified_dividends: Total S&P 500 qualified dividends stacked on top ($)
    - target_year: The exact calendar year being simulated (e.g., 2035)
    - inflation_factor: The expected annual inflation rate as a decimal (e.g., 0.023 for 2.3%)
    """
    # 1. 2026 Baseline Structural Tax Parameters (Single Status)
    ORDINARY_BRACKETS_2026 = [
        (12400.00, 0.10), (50400.00, 0.12), (105700.00, 0.22),
        (201775.00, 0.24), (256225.00, 0.32), (640600.00, 0.35), (float('inf'), 0.37)
    ]
    
    QUALIFIED_BRACKETS_2026 = [
        (49450.00, 0.00), (545500.00, 0.15), (float('inf'), 0.20)
    ]
    
    STANDARD_DEDUCTION_BASE = [(16100.00, 1.0)]

    # 2. Inflate the tax architecture dynamically using the passed inflation_factor
    current_ord_brackets = inflate_tax_brackets(ORDINARY_BRACKETS_2026, 2026, target_year, inflation_factor)
    current_qual_brackets = inflate_tax_brackets(QUALIFIED_BRACKETS_2026, 2026, target_year, inflation_factor)
    
    inflated_deduction_list = inflate_tax_brackets(STANDARD_DEDUCTION_BASE, 2026, target_year, inflation_factor)
    current_standard_deduction = inflated_deduction_list[0][0] # Extract raw dollar value out of the tuple list

    # 3. Compute Net Taxable Ordinary Income
    taxable_ordinary = max(0.0, ordinary_income - current_standard_deduction)
    
    # 4. Calculate Tax Owed on Ordinary Income
    ordinary_tax_owed = 0.0
    prev_limit = 0.0
    for limit, rate in current_ord_brackets:
        if taxable_ordinary > prev_limit:
            taxable_in_slice = min(taxable_ordinary, limit) - prev_limit
            ordinary_tax_owed += taxable_in_slice * rate
        prev_limit = limit

    # 5. Calculate Preferential Tax Owed on Qualified Dividends (Stacked Math)
    total_taxable_income = taxable_ordinary + qualified_dividends
    qualified_tax_owed = 0.0
    
    prev_limit = 0.0
    for limit, rate in current_qual_brackets:
        if total_taxable_income > prev_limit and taxable_ordinary < limit:
            slice_floor = max(taxable_ordinary, prev_limit)
            slice_ceiling = min(total_taxable_income, limit)
            
            dividend_in_slice = slice_ceiling - slice_floor
            if dividend_in_slice > 0:
                qualified_tax_owed += dividend_in_slice * rate
        prev_limit = limit

    # 5.1 Calculated Net Investment Income Tax
    niit_owed = calculate_niit(taxable_ordinary, qualified_dividends)

    # 6. Aggregate Total Liability
    total_tax_bill = ordinary_tax_owed + qualified_tax_owed + niit_owed
    return round(total_tax_bill, 2)

def calculate_inflated_spend(base_spend, base_year, target_year, inflation_factor):
    """
    Computes the inflation-adjusted annual spending required to maintain 
    the same baseline purchasing power in a future target year.
    
    Inputs:
    - base_spend: Your starting lifestyle cost in today's dollars (e.g., 50000.00)
    - base_year: The starting benchmark year for that baseline (e.g., 2026)
    - target_year: The future year you are currently simulating (e.g., 2045)
    - inflation_factor: The expected annual inflation rate as a decimal (e.g., 0.023)
    """
    years_elapsed = target_year - base_year
    
    # If the target year is the base year or in the past, return the baseline spend
    if years_elapsed <= 0:
        return round(base_spend, 2)
        
    # Future Cost = Present Cost * (1 + inflation_rate) ^ years
    inflated_spend = base_spend * ((1 + inflation_factor) ** years_elapsed)
    
    return round(inflated_spend, 2)

def calculate_niit(ordinary_income, qualified_dividends):
    """
    Computes the 3.8% Net Investment Income Tax (NIIT) for a Single filer.
    
    Inputs:
    - ordinary_income: Total ordinary income ($), which includes RMDs, 
                        Social Security inclusion, and Roth conversions.
    - qualified_dividends: Total investment income ($) from the taxable brokerage.
    
    Rule: 
      Tax is 3.8% of the LESSER of:
      1. Net Investment Income (qualified_dividends)
      2. The amount by which Modified AGI exceeds the $200,000 threshold.
    """
    # 1. NIIT Threshold for Single Filers (Statutory, NOT indexed for inflation)
    NIIT_THRESHOLD = 200000.00
    NIIT_RATE = 0.038
    
    # 2. Calculate Modified Adjusted Gross Income (MAGI)
    # Note: Traditional IRA distributions and Roth conversions count toward MAGI.
    magi = ordinary_income + qualified_dividends
    
    # 3. If total income is below the threshold, no NIIT is owed
    if magi <= NIIT_THRESHOLD:
        return 0.0
        
    # 4. Calculate the excess income above the threshold
    magi_excess = magi - NIIT_THRESHOLD
    
    # 5. Apply the "Lesser Of" rule
    taxable_base = min(qualified_dividends, magi_excess)
    
    # 6. Calculate total NIIT surtax
    niit_owed = taxable_base * NIIT_RATE
    
    return round(niit_owed, 2)

def calculate_ordinary_income(rmd, roth_conversion, social_security, other_taxable_income=0.0):
    """
    Computes total taxable Ordinary Income before deductions.
    Accounts for the progressive 50% and 85% inclusion thresholds for Social Security.
    
    Inputs:
    - rmd: Required Minimum Distribution taken from Traditional IRA ($)
    - roth_conversion: Amount converted from Traditional to Roth IRA ($)
    - social_security: Total gross Social Security benefits received ($)
    - other_taxable_income: Any other ordinary income (Wages, Interest, etc.) ($)
    """
    # 1. Base Adjusted Gross Income (AGI) excluding the Social Security portion
    base_agi = rmd + roth_conversion + other_taxable_income
    
    # 2. Calculate IRS 'Combined Income' (Provisional Income)
    # Formula: AGI + 50% of Social Security benefits
    combined_income = base_agi + (0.50 * social_security)
    
    # 3. Determine the Taxable Portion of Social Security (Single Filer statutory limits)
    taxable_ss = 0.0
    
    if combined_income > 34000:
        # High-income tier: Up to 85% of benefits are taxable
        # The IRS math is a multi-step formula, capped strictly at 85% of gross benefits
        tier2_taxable = min(4500.00, 0.50 * (min(combined_income, 34000) - 25000))
        tier3_taxable = 0.85 * (combined_income - 34000)
        taxable_ss = min(0.85 * social_security, tier2_taxable + tier3_taxable)
    elif combined_income > 25000:
        # Mid-income tier: Up to 50% of benefits are taxable
        taxable_ss = min(0.50 * social_security, 0.50 * (combined_income - 25000))
    else:
        # Low-income tier: 0% taxable
        taxable_ss = 0.0
        
    # 4. Total Taxable Ordinary Income
    total_ordinary_income = base_agi + taxable_ss
    
    return round(total_ordinary_income, 2)


def calculate_rmd(year, trad_ira_balance, birth_year=1975):
    """
    Computes the IRS Required Minimum Distribution (RMD).
    Based on the IRS Uniform Lifetime Table (Table III) for an individual filer.
    """
    # Determine age
    age = year - birth_year

    # 1. Determine the legal starting age under SECURE Act 2.0
    if birth_year >= 1960:
        rmd_start_age = 75
    else:
        rmd_start_age = 73

    # If the user hasn't reached RMD age yet, no distribution is required
    if age < rmd_start_age:
        return 0.0

    # 2. IRS Uniform Lifetime Table Divisors (Key: Age, Value: Divisor)
    # The divisor represents your remaining statistical life expectancy factor
    irs_uniform_table = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
        80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
        87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
        94: 9.5,  95: 8.9,  96: 8.4,  97: 7.8,  98: 7.3,  99: 6.8,  100: 6.4
    }

    # Grab the divisor. For ages over 100, we safely handle the scale:
    if age in irs_uniform_table:
        divisor = irs_uniform_table[age]
    elif age > 100:
        divisor = 6.0  # Safe floor approximation for extreme longevity
    else:
        divisor = 26.5 # Fallback safety guard

    # RMD Math: Prior Year-End Balance / Life Expectancy Factor
    rmd_amount = trad_ira_balance / divisor
    return round(rmd_amount, 2)

def inflate_tax_brackets(base_brackets, base_year, target_year, annual_inflation):
    """
    Takes a baseline set of tax brackets and adjusts the dollar thresholds 
    for inflation up to a target future year.
    
    Inputs:
    - base_brackets: List of tuples containing (dollar_limit, tax_rate)
    - base_year: The calendar year the brackets belong to (e.g., 2026)
    - target_year: The future year you want to calculate (e.g., 2050)
    - annual_inflation: Expected inflation rate as a decimal (e.g., 0.023 for 2.3%)
    """
    # Calculate the number of compounding years between the base year and target year
    years_elapsed = target_year - base_year
    
    # If the target year is in the past or the same year, return the base brackets unchanged
    if years_elapsed <= 0:
        return base_brackets
        
    inflated_brackets = []
    
    for limit, rate in base_brackets:
        # Check if the limit is the top 'infinity' bucket
        if limit == float('inf'):
            inflated_limit = float('inf')
        else:
            # Apply standard compound interest formula: Future Value = Present Value * (1 + r)^n
            # Rounding to the nearest dollar matches general IRS rounding practices
            inflated_limit = round(limit * ((1 + annual_inflation) ** years_elapsed), 2)
            
        inflated_brackets.append((inflated_limit, rate))
        
    return inflated_brackets

def generate_amounts(number_conversions, mode="random"):
    """
    Generates a list of amounts with length equal to number of conversions specified.
    
    Parameters:
    - mode (str): 'zero' to set all amounts to 0. 
                  'random' to select multiples of 1,000 between 0 and 50,000.
    """
    if mode == "zero":
        return [0] * number_conversions
    elif mode == "random":
        # Multiples of 1,000 from 0 up to 50,000
        options = [i * 1000 for i in range(51)] # [0, 1000, 2000, ..., 200000]
        return [random.choice(options) for _ in range(number_conversions)]
    else:
        raise ValueError("Invalid mode. Choose either 'zero' or 'random'.")


def calculate_final_amount (config, mode="random"):

    # Extract values from the config dictionary

    traditional_ira = config["traditional_ira"]
    roth_ira = config["roth_ira"]
    taxable_brokerage = config["taxable_brokerage"]
    base_spend = config["base_spend"]
    sp500_growth = config["sp500_growth"]
    div_rate = config["div_rate"]
    inflation_factor = config["inflation_factor"]
    birth_year = config["birth_year"]
    death_year = config["death_year"]
    first_year_of_conversions = config["first_year_of_conversions"]
    traditional_discount_factor = config["traditional_discount_factor"]

     # --- 1.1 GENERATE RANDOM OR ZERO'ED CONVERSION AMOUNTS
    number_conversions = birth_year + 74 - first_year_of_conversions #Use 75 because that is when RMD's begin to be required
    conversion_amounts = generate_amounts(number_conversions, mode)

    # --- 2. THE AUTOMATED LOOP ---
    # range(2027, death_year) runs from 2027 up to (but not including) death_year
    for current_year in range(first_year_of_conversions, death_year):
        
        # [B] Execute your financial math (Runs once per year automatically)

        # 1.01 Determine annual conversion
        # 1. Calculate how many years have passed since the start
        index = current_year - first_year_of_conversions
        # 2. If index is within the list, get the amount. Otherwise, set to 0.
        if index < len(conversion_amounts):
            annual_conversion = conversion_amounts[index]
        else:
            annual_conversion = 0
            
        # 1.1 Determine dividends received from the non-tax advantaged account
        divs_received = div_rate * taxable_brokerage

        # 1.2 Determine required minimum distribution
        rmd = calculate_rmd(current_year, traditional_ira, birth_year)

        # 1.3 Determine taxes owed
        if current_year >= birth_year + 62:
            social_security = 35628
        else:
            social_security = 0
        ordinary_income = calculate_ordinary_income(rmd, annual_conversion, social_security)

        taxes_owed = calculate_federal_tax(ordinary_income, divs_received, current_year, inflation_factor)

        # 1.4 Determine adjustments to taxable account
        annual_spend = calculate_inflated_spend(base_spend, first_year_of_conversions, current_year, inflation_factor)
        taxable_brokerage -= annual_spend

        taxable_brokerage += social_security
        taxable_brokerage += rmd
        taxable_brokerage += divs_received
        taxable_brokerage -= taxes_owed

        # check for bankruptcy
        if taxable_brokerage < 0:
            # Money to pay taxes on Roth conversion can only come out of an IRA without penalty after age 60
            if current_year < birth_year + 60:
                return 0, conversion_amounts
            else:
                roth_ira += taxable_brokerage
                taxable_brokerage = 0
       
        # 3. Execute the Roth conversion shift
        traditional_ira -= annual_conversion
        roth_ira += annual_conversion

        # 4.  Deduct rmd from traditional account
        traditional_ira -= rmd
        
        # 2. Apply S&P 500 growth to all balances for the next year
        traditional_ira *= (1 + sp500_growth)
        roth_ira *= (1 + sp500_growth)
        taxable_brokerage *= (1 + sp500_growth)

    final_amount = taxable_brokerage + roth_ira + traditional_ira * traditional_discount_factor

    return final_amount, conversion_amounts

def run_optimization_loop(config, iterations=10000):
    """
    Runs the full optimization simulation loop over a set number of iterations.
    Compares random conversion streams against a fixed baseline.
    """
    # 1. Establish the "zero conversion" baseline using the passed config dictionary
    final_amount, conversion_amounts = calculate_final_amount(config, "zero")
    
    print(f"Baseline (No Conversions): ${final_amount / 1000000:.2f} million")
    
    # Set up our tracking variables
    max_amount = final_amount
    max_conversion_stream = conversion_amounts

    # 2. Run the optimization search block
    print(f"Searching {iterations:,} random strategies for the optimal path...")

    for i in range(iterations):
        final_amount, conversion_amounts = calculate_final_amount(config, "random")
        
        if final_amount > max_amount:
            max_amount = final_amount
            max_conversion_stream = conversion_amounts

    # 3. Print the final winning totals and return them
    print("=========================================")
    print(f"🏆 OPTIMIZED ESTATE VALUE: ${max_amount / 1000000:.2f} million")
    print("=========================================")

    print("Optimal Annual Conversion Stream Found:")
    start_year = config["first_year_of_conversions"]
    
    for year_idx, amount in enumerate(max_conversion_stream):
        cal_year = start_year + year_idx
        print(f"  Year {cal_year}: ${amount:,.2f}")
    print("=========================================\n")
    
    return max_amount, max_conversion_stream

my_profile = {
    "traditional_ira": 1700000.00,
    "roth_ira": 0.00,
    "taxable_brokerage": 630000.00,
    "base_spend": 50000.00,
    "sp500_growth": 0.07,
    "div_rate": 0.013,
    "inflation_factor": 0.023,
    "birth_year": 1975,
    "death_year": 2065,
    "first_year_of_conversions": 2027,
    "traditional_discount_factor": 0.77
}

import streamlit as st
import pandas as pd  # Streamlit uses pandas dataframes to display tables beautifully

# 1. Add a visual title to the web page
st.title("🎯 Optimal Roth Conversion Calculator")
st.write("Adjust the parameters below to find your optimal conversion stream.")

# 2. Turn your parameters into interactive sidebar sliders and inputs
st.sidebar.header("User Financial Profile")

user_config = {
    "traditional_ira": st.sidebar.number_input("Traditional IRA Balance ($)", value=1700000.0, step=50000.0),
    "roth_ira": st.sidebar.number_input("Starting Roth IRA Balance ($)", value=0.0, step=10000.0),
    "taxable_brokerage": st.sidebar.number_input("Taxable Brokerage Balance ($)", value=1000000.0, step=50000.0),
    "base_spend": st.sidebar.slider("Annual Base Lifestyle Spend ($)", 20000, 200000, 50000),
    "sp500_growth": st.sidebar.slider("S&P 500 Growth Rate (%)", 3.0, 10.0, 7.0) / 100,
    "div_rate": 0.013,
    "inflation_factor": 0.023,
    "birth_year": st.sidebar.number_input("Birth Year", value=1975, step=1),
    "death_year": st.sidebar.number_input("Simulate Until Year (Death Year)", value=2065, step=1),
    "first_year_of_conversions": 2027,
    "traditional_discount_factor": st.sidebar.slider("Heir Tax Discount Factor (0.77 = 23% tax)", 0.50, 1.00, 0.77)
}

# 3. Add a big action button to trigger the simulation
if st.button("🚀 Run 10,000-Run Optimization Loop"):
    with st.spinner("Calculating optimal tax strategies..."):
        
        # Run your baseline logic using the interactive dictionary
        baseline_amount, _ = calculate_final_amount(user_config, mode="zero")
        
        # Run your optimization loop function (which returns max_amount and max_conversion_stream)
        max_amount, max_conversion_stream = run_optimization_loop(user_config, iterations=10000)
        
        # Print summary statistics onto the web page dashboard
        st.success("Optimization Complete!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Optimized Estate Value to Heirs", value=f"${max_amount / 1000000:.2f} Million")
        with col2:
            st.metric(label="Baseline Value (No Conversions)", value=f"${baseline_amount / 1000000:.2f} Million")
            
        tax_savings = (max_amount - baseline_amount) / 1000000
        if tax_savings > 0:
            st.write(f"📈 Converting saved your heirs **${tax_savings:.2f} Million** in tax drag!")
        else:
            st.write("📉 For this profile, a strategy of **Zero Conversions** is mathematically optimal.")

        # 🚨 NEW: Structure the schedule into a clean table for the user interface
        st.subheader("🗓️ Optimal Annual Conversion Schedule")
        st.write("This stream represents the highest scoring sequence discovered by the simulator:")
        
        # Build matching calendar years list
        start_year = user_config["first_year_of_conversions"]
        schedule_data = {
            "Calendar Year": [start_year + idx for idx in range(len(max_conversion_stream))],
            "Conversion Amount": max_conversion_stream
        }
        
        # Convert to a data framework layout
        df = pd.DataFrame(schedule_data)
        
        # Display the table with professional currency formatting
        st.dataframe(
            df.style.format({"Conversion Amount": "${:,.2f}"}),
            use_container_width=True,
            hide_index=True
        )

run_optimization_loop(my_profile)
