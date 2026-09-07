import streamlit as st

st.set_page_config(page_title="Documentation & Assumptions", page_icon="📖")

st.title("📖 Documentation & Model Assumptions")
st.write("Welcome to the reference manual. This page details how the engine evaluates your retirement profiles and explains the core baseline inputs.")

# --- SECTION 1: PARAMETER GLOSSARY ---
st.header("🗂️ 1. Parameter Definitions")

with st.expander("👤 Heir Tax Discount Factor (Default: 0.77)", expanded=True):
    st.write(
        "**What it means:** Traditional IRAs carry a 'hidden' tax debt. When your heirs inherit a Traditional IRA, "
        "the IRS requires them to withdraw the entire balance within 10 years (under the SECURE Act) and pay ordinary income taxes on it. "
        "The **Heir Tax Discount Factor** reduces the Traditional IRA's face value to accurately compare it against completely tax-free Roth assets."
    )
    st.info(
        "💡 **Why a 23% rate (0.77 factor) is an excellent default assumption:**\n\n"
        "Most adult children inheriting a large estate are in their peak earning years (40s and 50s). "
        "Under the 2026 post-sunset tax schedule, a Single filer earning between $50,400 and $105,700 falls into the **22% bracket**, "
        "while income between $105,700 and $201,775 falls into the **24% bracket**. "
        "An assumed **23% tax drag** perfectly splits this middle-class sweet spot. "
        "If you expect your heirs to be high-earning professionals, you should slide this factor lower (e.g., 0.68 for a 32% tax rate)."
    )

with st.expander("📈 Investment Growth Rate (Default: 7.0%)"):
    st.write(
        "**What it means:** The compounding annual return applied to your Trad IRA, Roth IRA, and Taxable Brokerage cash. "
        "Because this model automatically inflates your annual spending, brackets, and deductions using your *Inflation Factor*, "
        "this input should represent a **Real Return Rate** (growth adjusted for inflation) rather than a nominal rate."
    )

with st.expander("💸 Dividend Rate (Default: 1.3%)"):
    st.write(
        "**What it means:** The annual yield generated strictly by your Taxable Brokerage balance, modeled after a standard S&P 500 index fund. "
        "This income flows directly into your ordinary income and MAGI tax tracks every year as **Qualified Dividends**."
    )

# --- SECTION 2: HARDCODED MODEL ASSUMPTIONS ---
st.header("⚙️ 2. Structural Model Assumptions")
st.write("To maintain mathematical consistency, the underlying simulation engine relies on the following hardcoded baseline parameters:")

st.subheader("🇺🇸 Federal Tax Architecture")
st.markdown(
    "- **Single Filer Status:** The tax engine evaluates all ordinary income and qualified dividend stacking tiers using Single status limits.\n"
    "- **Post-Sunset Brackets (2026+):** All math utilizes the statutory structural reversion rates scheduled after the expiration of the 2017 Tax Cuts and Jobs Act.\n"
    "- **Standard Deduction:** The engine assumes the user takes the standard single deduction (Baseline: $16,100, dynamically adjusted for inflation annually)."
)

st.subheader("👵 Social Security Mechanics")
st.markdown(
    "- **Age 62 Claiming:** The program locks in Social Security cash inflows to automatically begin the exact year the user turns 62.\n"
    "- **Maximum Benefit Allocation:** The benefit is hardcoded to a fixed baseline of **$35,628 per year** ($2,969/month), assuming the user qualified for the maximum possible earnings record prior to taking early retirement.\n"
    "- **Provisional Income Squeeze:** The engine routes this benefit through the exact multi-tier IRS inclusion thresholds ($25,000 / $34,000 combined income lines) to dynamically subject up to 85% of your benefits to ordinary income tax based on your annual conversion streams."
)

st.subheader("🛑 Conversion Cutoffs")
st.markdown(
    "- **Age 74 Hard Stop:** In accordance with your strategic intent, the optimization algorithm completely disables all Roth conversions the year the user turns 75. This eliminates any overlapping tax drag once Required Minimum Distributions (RMDs) are legally mandated."
)
