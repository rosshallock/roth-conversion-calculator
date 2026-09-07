
#=====================================================================
#ROTH CONVERSION CALCULATOR & ESTATE OPTIMIZATION ENGINE
#=====================================================================
"""
Purpose:
  Simulates a financial timeline to 
  determine the optimal multi-year Roth conversion schedule. 
  
Strategy & Methodology:
  - Generates an active conversion stream (terminating at age 75 
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

def calculate_irmaa_surcharge(magi_two_years_prior, current_year, birth_year, inflation_factor):
    """
    Computes the annual Medicare IRMAA surcharge penalty for a Single filer.
    Uses the 2-year lookback rule: Checks if current age is 65+, but evaluates 
    the past income against thresholds inflated to that past lookback year.
    """
    current_age = current_year - birth_year
    if current_age < 65:
        return 0.0

    lookback_year = current_year - 2

    # 1. 2026 Baseline Statutory IRMAA Tiers
    IRMAA_TIERS_2026 = [
        (106000.00, 0.00, 0.00),     # Base Tier 
        (133000.00, 74.00, 13.00),   # Tier 1
        (166000.00, 185.00, 34.00),  # Tier 2
        (199000.00, 296.00, 55.00),  # Tier 3
        (414000.00, 407.00, 76.00),  # Tier 4
        (float('inf'), 444.00, 83.00) # Tier 5
    ]
    
    # 2. Inflate the limits locally to handle the 3-item tuple rows safely
    years_elapsed = lookback_year - 2026
    
    chosen_b_surcharge = 0.0
    chosen_d_surcharge = 0.0
    
    for limit, b_rate, d_rate in IRMAA_TIERS_2026:
        # Calculate the inflation-adjusted ceiling for this tier
        if limit == float('inf'):
            inflated_limit = float('inf')
        else:
            inflated_limit = round(limit * ((1 + inflation_factor) ** years_elapsed), 2)
            
        # Check if income fits inside this inflated threshold
        if magi_two_years_prior <= inflated_limit:
            chosen_b_surcharge = b_rate
            chosen_d_surcharge = d_rate
            break  # Exit loop immediately once the correct tier is locked in#

           
    # 3. Convert monthly surcharges into a total annual cash out-of-pocket penalty

    total_annual_irmaa = (chosen_b_surcharge + chosen_d_surcharge) * 12
    return round(total_annual_irmaa, 2)

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


def calculate_final_amount (config, mode="random", fixed_tokens=None):

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
    other_income = config["other_income"]

    # Initialize containers for tracking
    conversion_amounts = []
    portfolio_timeline = []
    token_history = []
    # The token_history tracks which strategy was chosen each year.
    # 0 = zero conversion.
    # 1 = fill 12% bracket
    # 2 = fill 22% bracket
    # 3 = fill 24% bracket
    # 4 = fill to Tier 1 IRMAA cliff
    # 5 = fill to Tier 2 IRMAA cliff
    historical_magi = []

    # --- 1. THE AUTOMATED LOOP ---
    # range(2027, death_year) runs from 2027 up to (but not including) death_year
    for current_year in range(first_year_of_conversions, death_year):

        age = current_year - birth_year
        index = current_year - first_year_of_conversions

        # [B] Execute your financial math (Runs once per year automatically)

            
        # 1.1 Determine dividends received from the non-tax advantaged account
        divs_received = div_rate * taxable_brokerage

        # 1.2 Determine required minimum distribution
        rmd = calculate_rmd(current_year, traditional_ira, birth_year)

        # 1.3 Determine social security
        if age >= 62:
            social_security = 35628
        else:
            social_security = 0

        # 1.4 Determine annual conversion amount

        # 1.4.1 If determining baseline, set all conversion amounts to zero

        # 1.4.3 For each year prior to age 75, pick a random conversion amount that is either zero or
        # an amount that fills a bracket.  
             
        if age > 74:
            annual_conversion = 0
        
        else:
            # 1.4.1 If determining baseline, set all conversion amounts to zero
            if mode == "zero":
                annual_conversion = 0
                chosen_token = 0

            # Otherwise pick a random conversion amount that is either zero or a number that fills a bracket
            else:
                #set the conversion amount equal to zero to determine ordinary income before any conversion
                pre_conversion_ordinary = calculate_ordinary_income(rmd, 0, social_security, other_income)

                #Call a function that returns all options explicitly
                room_12, room_22, room_24, room_irmaa_1, room_irmaa_2, room_div_15, room_niit, room_div_20 = get_all_options(pre_conversion_ordinary, current_year, config)
                options_pool = [0.0, room_12, room_22, room_24, room_irmaa_1, room_irmaa_2, room_div_15, room_niit, room_div_20]

                if fixed_tokens is not None and index< len(fixed_tokens):
                    #Hill climber mode: Use the specific bracket strategy forced
                    chosen_token = fixed_tokens[index]
                    annual_conversion = options_pool[chosen_token]

                else:
                    #Random search mode: Randomly pick one of the 9 conversion strategies
                    chosen_token = random.choice(range(9))
                    annual_conversion = options_pool[chosen_token]

            # Fill in the conversion_amounts container
            conversion_amounts.append(annual_conversion)
            token_history.append(chosen_token)

        #1.5.1 Calculate current year ordinary income and MAGI
            
        ordinary_income = calculate_ordinary_income(rmd, annual_conversion, social_security, other_income)
        current_year_magi = ordinary_income + divs_received

        #1.5.2 Save current MAGI into our historical list so future years can read
        historical_magi.append(current_year_magi)

        #1.5.3 Determine taxes owed after conversion

        taxes_owed = calculate_federal_tax(ordinary_income, divs_received, current_year, inflation_factor)

        # 1.6 Calculate Medicare IRMAA surcharges
        lookback_index = index - 2

        if lookback_index >= 0:
            lookback_magi = historical_magi[lookback_index]
            
            # We call IRMAA using the historical income and the inflation factor of that lookback year
            irmaa_surcharge = calculate_irmaa_surcharge(
                lookback_magi, current_year, birth_year, inflation_factor
            )
        else:
            # Fallback for the first two years of the simulation if the user was somehow already 65+
            irmaa_surcharge = 0.0

        # 2. Determine adjustments to taxable account
        annual_spend = calculate_inflated_spend(base_spend, first_year_of_conversions, current_year, inflation_factor)
        taxable_brokerage -= annual_spend

        taxable_brokerage += social_security
        taxable_brokerage += rmd
        taxable_brokerage += divs_received
        taxable_brokerage += other_income
        taxable_brokerage -= taxes_owed
        taxable_brokerage -= irmaa_surcharge

        # check for bankruptcy
        if taxable_brokerage < 0:
            # Money to pay taxes on Roth conversion can only come out of an IRA without penalty after age 60
            if age < 60:
                return 0, conversion_amounts, [], []
            else:
                roth_ira += taxable_brokerage
                taxable_brokerage = 0
                if roth_ira < 0:
                    traditional_ira += roth_ira
                    roth_ira = 0
                    if traditional_ira < 0:
                        return 0, conversion_amounts, [], []
       
        # 3. Execute the Roth conversion shift
        traditional_ira -= annual_conversion
        roth_ira += annual_conversion

        # 4.  Deduct rmd from traditional account
        traditional_ira -= rmd
        
        # 5. Apply S&P 500 growth to all balances for the next year
        traditional_ira *= (1 + sp500_growth)
        roth_ira *= (1 + sp500_growth)
        taxable_brokerage *= (1 + sp500_growth)

        #6 Keep track of portfolio over time
        snapshot = {
            "Year": current_year,
            "Trad IRA": round(traditional_ira, 2),
            "Roth IRA": round(roth_ira, 2),
            "Taxable": round(taxable_brokerage, 2),
            "Taxes Owed": round(taxes_owed, 2)
        }

        portfolio_timeline.append(snapshot)

    final_amount = taxable_brokerage + roth_ira + traditional_ira * traditional_discount_factor

    return final_amount, conversion_amounts, portfolio_timeline, token_history

def generic_hill_climb_polish(config, starting_tokens, starting_amount, steps=300):
    """
    Generically polishes ANY incoming token list strategy by iteratively 
    tweaking random years to alternative bracket strategies.
    """
    current_best_amount = starting_amount
    current_best_tokens = list(starting_tokens)
    
    for _ in range(steps):
        random_year_idx = random.randint(0, len(current_best_tokens) - 1)
        original_token = current_best_tokens[random_year_idx]
        
        # Select from alternative strategy tokens (0=zero, 1=12%, 2=22%, 3=24%)
        alternatives = [t for t in range(9) if t != original_token]
        tweaked_token = random.choice(alternatives)
        
        current_best_tokens[random_year_idx] = tweaked_token
        
        # Evaluate the tweaked sequence
        test_amount, _, _, _ = calculate_final_amount(config, mode="random", fixed_tokens=current_best_tokens)
        
        if test_amount > current_best_amount:
            current_best_amount = test_amount
        else:
            current_best_tokens[random_year_idx] = original_token
            
    # Extract final clean timeline details for the winner
    final_amt, final_stream, final_timeline, final_tokens = calculate_final_amount(
        config, mode="random", fixed_tokens=current_best_tokens
    )
    return final_amt, final_stream, final_timeline, final_tokens

def get_all_options(pre_conversion_ordinary, current_year, config):
    """
    Determines the exact conversion amounts needed to fill the 12%, 22%, and 24% 
    tax brackets for the current year, as well as the Tier 1 and Tier 2 Medicare IRMAA surcharge cliffs,
    NIIT thresholds, and preferential qualified dividend capital gains jumps
    """
    # 1. Unpack structural inflation factor from config
    inflation_factor = config["inflation_factor"]

    # 2. Baseline Structural Tax Parameters (2026 Single Status)
    ORDINARY_BRACKETS_2026 = [
        (12400.00, 0.10), (50400.00, 0.12), (105700.00, 0.22),
        (201775.00, 0.24), (256225.00, 0.32), (640600.00, 0.35), (float('inf'), 0.37)
    ]

    QUALIFIED_BRACKETS_2026 = [(49450.00, 0.00), (545500.00, 0.15), (float('inf'), 0.20)]

    STANDARD_DEDUCTION_BASE = [(16100.00, 1.0)]

    # 3. Inflate the brackets and standard deduction for the simulated year
    current_ord_brackets = inflate_tax_brackets(ORDINARY_BRACKETS_2026, 2026, current_year, inflation_factor)
    current_qual_brackets = inflate_tax_brackets(QUALIFIED_BRACKETS_2026, 2026, current_year, inflation_factor)
    inflated_deduction_list = inflate_tax_brackets(STANDARD_DEDUCTION_BASE, 2026, current_year, inflation_factor)
    current_standard_deduction = inflated_deduction_list[0][0]

    # 4. Extract top boundaries for target brackets
    top_of_12_bracket = current_ord_brackets[1][0]  # The $50,400 line (inflated)
    top_of_22_bracket = current_ord_brackets[2][0]  # The $105,700 line (inflated)
    top_of_24_bracket = current_ord_brackets[3][0]  # The $201,775 line (inflated)

    # 4.1 🚨 Dynamically inflate the IRMAA baseline cliffs for this future year
    # We apply the same inflation rule to the baseline $106k and $133k statutory limits.
    max_magi_irmaa_1 = round(106000.00 * ((1 + inflation_factor) ** (current_year - 2026)), 2)
    max_magi_irmaa_2 = round(133000.00 * ((1 + inflation_factor) ** (current_year - 2026)), 2)


    # 5. Calculate Gross Gross Caps (Bracket Boundary + Standard Deduction)
    max_gross_for_12 = top_of_12_bracket + current_standard_deduction
    max_gross_for_22 = top_of_22_bracket + current_standard_deduction
    max_gross_for_24 = top_of_24_bracket + current_standard_deduction

    # Preferential Capital Gains & NIIT Targets
    # Note: Capital gains brackets apply to Net Taxable Ordinary Income (Gross minus Standard Deduction)
    max_taxable_div_jump_15 = current_qual_brackets[0][0]
    max_taxable_div_jump_20 = current_qual_brackets[1][0]
    
    # Gross Targets = Taxable target + Standard Deduction
    max_gross_div_15 = max_taxable_div_jump_15 + current_standard_deduction
    max_gross_div_20 = max_taxable_div_jump_20 + current_standard_deduction
    
    # NIIT applies to MAGI directly (unadjusted for inflation)
    max_magi_niit = 200000.00

    # 6. Calculate remaining space (Floor at 0.0 if other income already fills it)
    room_in_12 = max(0.0, max_gross_for_12 - pre_conversion_ordinary)
    room_in_22 = max(0.0, max_gross_for_22 - pre_conversion_ordinary)
    room_in_24 = max(0.0, max_gross_for_24 - pre_conversion_ordinary)

    # For IRMAA space, we subtract ordinary income directly because IRMAA limits apply to MAGI
    room_irmaa_1 = max(0.0, max_magi_irmaa_1 - pre_conversion_ordinary)
    room_irmaa_2 = max(0.0, max_magi_irmaa_2 - pre_conversion_ordinary)

    room_div_15 = max(0.0, max_gross_div_15 - pre_conversion_ordinary)
    room_niit = max(0.0, max_magi_niit - pre_conversion_ordinary)
    room_div_20 = max(0.0, max_gross_div_20 - pre_conversion_ordinary)

    return round(room_in_12, 2), round(room_in_22, 2), round(room_in_24, 2), round(room_irmaa_1), round(room_irmaa_2), round(room_div_15), round(room_niit), round(room_div_20)

def run_optimization_loop(config, iterations=10000):
    """
    Runs an exploratory random token search to find the Top 5 unique strategy candidates,
    then automatically passes each through a Hill Climbing polisher to find the
    absolute precision maximum estate value.
    """
    # 1. Establish the "zero conversion" baseline floor
    baseline_amount, baseline_stream, baseline_timeline, baseline_tokens = calculate_final_amount(config, "zero")
    print(f"Baseline Value (No Conversions): ${baseline_amount / 1000000:.2f} million")
    
    # 2. Exploratory Phase: Gather the Top 5 Unique Strategies
    top_strategies = []  # Will hold tuples of (final_amount, token_list)
    
    print(f"Searching {iterations:,} random token combinations to map the tax brackets...")
    for i in range(iterations):
        amt, stream, timeline, tokens = calculate_final_amount(config, mode="random")
        
        # Ignore failed bankrupt runs (where return score is 0)
        if amt <= 0:
            continue
            
        # Add to candidate pool, sort by highest amount, and keep strictly the top 5
        top_strategies.append((amt, tokens))
        top_strategies.sort(key=lambda x: x[0], reverse=True)
        top_strategies = top_strategies[:5]

    print("\n--- Top 5 Random Candidates Discovered ---")
    for idx, (amt, _) in enumerate(top_strategies):
        print(f"  Candidate #{idx+1}: ${amt / 1000000:.2f} million")

    # 3. Precision Phase: Run Hill Climbing on all Top 5 candidates
    print("\nPolishing all top candidates via Hill Climbing...")
    
    absolute_best_amount = baseline_amount
    absolute_best_stream = []
    absolute_best_timeline = []
    absolute_best_tokens = []

    for idx, (amt, tokens) in enumerate(top_strategies):
        # Pass each candidate to the generic polisher
        polished_amt, polished_stream, polished_timeline, polished_tokens = generic_hill_climb_polish(
            config, tokens, amt, steps=300
        )
        print(f"  Candidate #{idx+1} polished from ${amt / 1000000:.2f}M -> ${polished_amt / 1000000:.2f}M")
        
        # Track the absolute winner across all 5 polished tracks
        if polished_amt > absolute_best_amount:
            absolute_best_amount = polished_amt
            absolute_best_stream = polished_stream
            absolute_best_timeline = polished_timeline
            absolute_best_tokens = polished_tokens

    # GLITCH FIX: If the baseline "do nothing" strategy won, the lists are empty.
    # We populate them with the baseline arrays so the console and Streamlit have data to show.
    if absolute_best_amount == baseline_amount or len(absolute_best_stream) == 0:
        absolute_best_amount = baseline_amount
        absolute_best_stream = baseline_stream if len(baseline_stream) > 0 else [0.0] * number_conversions
        absolute_best_timeline = baseline_timeline
        absolute_best_tokens = baseline_tokens if len(baseline_tokens) > 0 else [0] * number_conversions

    print("\n=========================================")
    print(f"🏆 ULTIMATE HYBRID OPTIMIZED ESTATE VALUE: ${absolute_best_amount / 1000000:.2f} million")
    print("=========================================")
    
    # 🚨 NEW: Loop through and print out the ultimate conversion schedule beautifully
    print("Optimal Annual Conversion Stream Found After Polishing:")
    start_year = config["first_year_of_conversions"]
    
    # Text mapping to translate tokens into friendly labels
    strategy_mapping = {
                0: "Zero Conversion",
                1: "Fill 12% Bracket",
                2: "Fill 22% Bracket",
                3: "Fill 24% Bracket",
                4: "Fill to IRMAA Tier 1 Cliff ($106k)",
                5: "Fill to IRMAA Tier 2 Cliff ($133k)",
                6: "Fill to 15% Dividend Tax Jump",
                7: "Fill to NIIT Surtax Limit ($200k)",
                8: "Fill to 20% Dividend Tax Jump"
    }

    for year_idx, amount in enumerate(absolute_best_stream):
        cal_year = start_year + year_idx

        # Look up the token matching this exact year from the absolute_best_tokens array
        chosen_token = absolute_best_tokens[year_idx]
        strategy_name = strategy_mapping[chosen_token]
        
        print(f"  Year {cal_year}: ${amount:,.2f} -> {strategy_name}")
        
    print("=========================================\n")

# Return the absolute champion's data to the Streamlit UI dashboard
    return absolute_best_amount, absolute_best_stream, absolute_best_timeline, absolute_best_tokens

my_profile = {
    "traditional_ira": 1700000.00,
    "roth_ira": 0.00,
    "taxable_brokerage": 1000000.00,
    "base_spend": 100000.00,
    "sp500_growth": 0.07,
    "div_rate": 0.013,
    "inflation_factor": 0.023,
    "birth_year": 1975,
    "death_year": 2065,
    "first_year_of_conversions": 2027,
    "traditional_discount_factor": 0.77,
    "other_income": 0
}

import streamlit as st
import pandas as pd  # Streamlit uses pandas dataframes to display tables beautifully

# 1. Add a visual title to the web page
st.title("🎯 Optimal Roth Conversion Calculator")
st.write("Adjust the parameters below to find your optimal conversion stream.")

# 2. Turn your parameters into interactive sidebar sliders and inputs
st.sidebar.header("User Financial Profile")

user_config = {
    "traditional_ira": st.sidebar.number_input("Traditional IRA Balance ($)", value=1700000.0, step=10000.0),
    "roth_ira": st.sidebar.number_input("Starting Roth IRA Balance ($)", value=0.0, step=10000.0),
    "taxable_brokerage": st.sidebar.number_input("Taxable Brokerage Balance ($)", value=1000000.0, step=10000.0),
    "base_spend": st.sidebar.slider("Annual Base Lifestyle Spend ($)", 20000, 500000, 100000, step=1000),
    "sp500_growth": st.sidebar.slider("S&P 500 Growth Rate (%)", 0.0, 10.0, 7.0) / 100,
    "div_rate": 0.013,
    "inflation_factor": 0.023,
    "birth_year": st.sidebar.number_input("Birth Year", value=1975, step=1),
    "death_year": st.sidebar.number_input("Simulate Until Year (Death Year)", value=2065, step=1),
    "first_year_of_conversions": 2027,
    "traditional_discount_factor": st.sidebar.slider("Heir Tax Discount Factor (0.77 = 23% tax rate)", 0.50, 1.00, 0.77),
    "other_income": st.sidebar.number_input("Fixed Annual Other Income / Pension ($)", value=0.0, step=5000.0)
}

# 3. Add a big action button to trigger the simulation
if st.button("🚀 Run 10,000-Run Optimization Loop"):

    # Calculate starting age when the button is clicked
    start_year = user_config["first_year_of_conversions"]
    birth_year = user_config["birth_year"]
    starting_age = start_year - birth_year

    # 🚨 NEW: Check the age requirement AFTER clicking the button
    if starting_age >= 75:
        st.warning(f"⚠️ **Notice: Conversion Window Closed**")
        st.write(
            f"In your starting year of {start_year}, your age is **{starting_age}**. "
            "Because Required Minimum Distributions (RMDs) have already begun or are starting immediately, "
            "additional Roth conversions are generally no longer tax-efficient for this profile. "
            "A **Zero Conversion** strategy is mathematically optimal past age 74."
        )
    else:


        with st.spinner("Calculating optimal tax strategies..."):
            
            # Run your baseline logic using the interactive dictionary
            baseline_amount, _, _, _ = calculate_final_amount(user_config, mode="zero")
            
            # Run your optimization loop function (which returns max_amount and max_conversion_stream)
            max_amount, max_conversion_stream, best_timeline, best_tokens = run_optimization_loop(user_config, iterations=10000)
            
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

            st.subheader("🗓️ Optimal Annual Conversion Schedule")

            # Dictionary map to translate token numbers into readable text strings
            strategy_mapping = {
                0: "Zero Conversion",
                1: "Fill 12% Bracket",
                2: "Fill 22% Bracket",
                3: "Fill 24% Bracket",
                4: "Fill to IRMAA Tier 1 Cliff",
                5: "Fill to IRMAA Tier 2 Cliff",
                6: "Fill to 15% Dividend Tax Jump",
                7: "Fill to NIIT Surtax Limit",
                8: "Fill to 20% Dividend Tax Jump"
            }
            # Translate your raw token history list into text strings
            strategy_names = [strategy_mapping[token] for token in best_tokens]

            st.write("This stream represents the highest scoring sequence discovered by the simulator:")
            
            # Build matching calendar years list
            start_year = user_config["first_year_of_conversions"]
            schedule_data = {
                "Calendar Year": [start_year + idx for idx in range(len(max_conversion_stream))],
                "Conversion Amount": max_conversion_stream,
                "Tax Strategy Chosen": strategy_names
            }
            
            # Convert to a data framework layout
            df = pd.DataFrame(schedule_data)
            
            # Display the table with professional currency formatting
            st.dataframe(
                df.style.format({"Conversion Amount": "${:,.2f}"}),
                use_container_width=True,
                hide_index=True
            )

            # Visual Balance Projection Chart
            st.subheader("📈 50-Year Portfolio Value Projection")
            st.write("Track how your account balances shift over time under your optimized conversion strategy:")

            # 1. Convert the best_timeline list of dictionaries into a Pandas DataFrame
            chart_df = pd.DataFrame(best_timeline)

             # 1.1: Force the 'Year' column entries to be read as string characters to wipe out the formatting commas
            chart_df["Year"] = chart_df["Year"].astype(str)

            # 2. Re-index the DataFrame rows by 'Year' so the horizontal axis plots chronologically
            chart_df = chart_df.set_index("Year")

            # 3. Filter out 'Taxes Owed' so the chart strictly focuses on your asset pools
            asset_chart_df = chart_df[["Trad IRA", "Roth IRA", "Taxable"]]

            # 4. Generate the fully interactive line chart widget
            st.line_chart(asset_chart_df, use_container_width=True)


run_optimization_loop(my_profile)
