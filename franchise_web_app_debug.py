import streamlit as st
import pandas as pd
import re

# ---------- CONFIG ----------
DATA_FILE = "/Users/johnconstantine/PyCharmMiscProject/ifpg_dataset.xlsx"
RESULT_LIMIT = 10
# ----------------------------

# ---------- LOAD + CLEAN ----------
try:
    df = pd.read_excel(DATA_FILE)
except FileNotFoundError:
    st.error(f"Could not find the dataset file:\n{DATA_FILE}")
    st.stop()

df.columns = df.columns.str.strip().str.lower()
df.replace(r"_x000D_", " ", regex=True, inplace=True)
# -----------------------------------

# ---------- PAGE TITLE ----------
st.set_page_config(page_title="Franchise Fit Finder")
st.title("Franchise Fit Finder 🌟")
st.write("Answer the questions below to get your personalized franchise short‑list.")
# --------------------------------

# ---------- QUESTIONS ----------
liquid_capital = st.selectbox(
    "Liquid capital available today?",
    ["Please select", "Under $50k", "$50k-$99k", "$100k-$249k", "$250k+"],
)

finance = st.checkbox("Are you willing to finance beyond that cash?")

hands_on_time = st.selectbox(
    "Hands-on time once running?",
    ["Please select", "Full-time owner-operator", "5-20 hrs/week (semi-absentee)", "<5 hrs/week (passive)"],
)

work_setting = st.selectbox(
    "Preferred daily work setting?",
    ["Please select", "Mostly outdoors / in-field", "Office / professional", "Home-based / mobile"],
)

industry_tags = sorted({t.strip() for cell in df["industry"].dropna() for t in str(cell).split(",")})
industry_interests = st.multiselect("Which industries are you most interested in?", industry_tags)

customer_type = st.selectbox(
    "Who would you rather sell to?", ["Please select", "Businesses (B2B)", "Consumers (B2C)", "Both"]
)
# ----------------------------------

if st.button("Find My Matches 🚀"):

    if (
        "Please select" in [liquid_capital, hands_on_time, work_setting, customer_type]
        or not industry_interests
    ):
        st.warning("Please complete every field and choose at least one industry.")
        st.stop()

    # ---------- FILTER PIPELINE ----------
    cap_map = {"Under $50k": 50_000, "$50k-$99k": 99_000, "$100k-$249k": 249_000, "$250k+": 1_000_000}
    cap_limit = cap_map[liquid_capital] * (2 if finance else 1)

    df_f = df.copy()
    df_f["cash required low"] = (
        df_f["cash required"].str.extract(r"(\d[\d,]*)").replace({",": ""}, regex=True).astype(float)
    )
    df_f = df_f[df_f["cash required low"] <= cap_limit]

    if hands_on_time == "5-20 hrs/week (semi-absentee)":
        df_f = df_f[df_f["semi-absentee ownership"] == "Yes"]
    elif hands_on_time == "<5 hrs/week (passive)":
        df_f = df_f[df_f["passive franchise"] == "Yes"]

    if work_setting == "Mostly outdoors / in-field":
        df_f = df_f[df_f["industry"].str.contains("home services|repair|restoration|lawn|pest", case=False, na=False)]
    elif work_setting == "Office / professional":
        df_f = df_f[df_f["industry"].str.contains("advertising|real estate|business services", case=False, na=False)]
    elif work_setting == "Home-based / mobile":
        df_f = df_f[df_f["home based franchise"] == "Yes"]

    df_f = df_f[df_f["industry"].apply(lambda x: any(tag in str(x) for tag in industry_interests))]

    if customer_type == "Businesses (B2B)":
        df_f = df_f[df_f["b2b"] == "Yes"]
    elif customer_type == "Consumers (B2C)":
        df_f = df_f[df_f["b2c"] == "Yes"]

    df_f = df_f.sort_values("industry_ranking")

    # ---------- FALLBACK ----------
    if df_f.empty:
        st.info("No brand met *all* filters. Showing top‑ranked companies inside your chosen industries instead.")
        df_f = (
            df[df["industry"].apply(lambda x: any(tag in str(x) for tag in industry_interests))]
            .sort_values("industry_ranking")
            .groupby("industry", sort=False)
            .head(1)
        )

    top_n = df_f.head(RESULT_LIMIT)
    if top_n.empty:
        st.error("Still nothing to display — please broaden your answers.")
        st.stop()

    # ---------- CSS ----------
    st.markdown(
        """
        <style>
        .rec {font-family: Helvetica, sans-serif; font-size: 16px; line-height: 1.45em;}
        .rec h3 {font-size: 24px; margin-bottom: 4px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- DISPLAY ----------
    st.subheader(f"✨ Your Top {len(top_n)} Franchise Recommendations ✨")

    def clean_money(s: str) -> str:
        if s is None or pd.isna(s):
            return "contact us for details"
        # remove any spaces, ensure single $
        s = re.sub(r"\s+", "", str(s))
        s = s.replace("$$", "$")
        if not s.startswith("$"):
            s = "$" + s.lstrip("$")
        return s

    for _, row in top_n.iterrows():
        def val(col):
            return row[col] if col in row and pd.notna(row[col]) else "contact us for details"

        startup_cost   = clean_money(row["cash required"]) if "cash required" in row else "contact us for details"
        franchise_fee  = clean_money(val("franchise fee - one unit"))
        veteran_disc   = val("veteran discount")
        brand          = row["franchise name"]
        link           = f"[{brand}]({val('url')})" if val("url") != "contact us for details" else brand

        st.markdown('<div class="rec">', unsafe_allow_html=True)
        st.markdown(f"### {link}", unsafe_allow_html=True)
        st.markdown(f"**Industry:** {val('industry')}")
        st.markdown(f"**Description:** {val('business summary')}")
        st.markdown(f"**Startup Cost:** {startup_cost}")
        st.markdown(f"**Franchise Fee:** {franchise_fee}")
        st.markdown(f"**Veteran Discount:** {veteran_disc}")
        st.markdown(f"**Industry Ranking:** {val('industry_ranking')}")
        st.markdown(f"**Number of Units Open:** {val('number of units open')}")
        st.markdown(f"**Support:** {val('support')}")
        st.markdown("</div><hr>", unsafe_allow_html=True)
