import streamlit as st
import pandas as pd
import re
from pathlib import Path

# ---------- CONFIG ----------
DATA_FILE   = "ifpg_dataset.xlsx"
MAP_FILE    = "industry to business type.xlsx"   # mapping sheet: business_type | industry
RESULT_LIMIT = 10
# ----------------------------

# ---------- LOAD MAIN DATA ----------
try:
    df = pd.read_excel(DATA_FILE)
except FileNotFoundError:
    st.error(f"Could not find the dataset file: {DATA_FILE}")
    st.stop()

df.columns = df.columns.str.strip().str.lower()
df.replace(r"_x000D_", " ", regex=True, inplace=True)
# ------------------------------------

# ---------- LOAD BUSINESS‑FOCUS MAP ----------
if not Path(MAP_FILE).exists():
    st.error(f"Mapping file '{MAP_FILE}' not found.")
    st.stop()

map_df = pd.read_excel(MAP_FILE)
map_df.columns = map_df.columns.str.strip().str.lower()

if not {"business_type", "industry"}.issubset(set(map_df.columns)):
    st.error("Mapping sheet must have columns 'business_type' and 'industry'.")
    st.stop()

biz_map = (map_df.groupby("business_type")["industry"]
                    .apply(list).to_dict())
biz_options = sorted(biz_map.keys())
# ------------------------------------

# ---------- PAGE TITLE ----------
st.set_page_config(page_title="Franchise Fit Finder")
st.title("Franchise Fit Finder 🌟")
st.write("Answer the questions below to get your personalized franchise short‑list.")
# --------------------------------

# ---------- OPTIONAL CONTACT INFO ----------
name  = st.text_input("Your Name (optional)")
email = st.text_input("Your Email (optional)")
phone = st.text_input("Your Phone (optional)")
# ------------------------------------------

# ---------- BUSINESS FOCUS (NEW) ----------
biz_focus = st.multiselect(
    "Type of Business / Business Focus you prefer  *(pick up to 3)*",
    biz_options,
    max_selections=3
)
# ------------------------------------------

# ---------- OTHER QUESTIONS ----------
liquid_capital = st.selectbox(
    "Liquid capital available today?",
    ["Please select", "Under $50k", "$50k-$99k", "$100k-$249k", "$250k+"],
)

finance = st.checkbox("Are you willing to finance beyond that cash?")

hands_on_time = st.selectbox(
    "Hands-on time once running?",
    ["Please select", "Full-time owner-operator",
     "5-20 hrs/week (semi-absentee)", "<5 hrs/week (passive)"],
)

industry_tags = sorted({t.strip() for cell in df["industry"].dropna()
                        for t in str(cell).split(",")})
industry_interests = st.multiselect(
    "Which industries are you most interested in? (optional)",
    industry_tags
)

customer_type = st.selectbox(
    "Who would you rather sell to?",
    ["Please select", "Businesses (B2B)", "Consumers (B2C)", "Both"]
)
# ------------------------------------------

# ---------- BUTTON ----------
if st.button("Find My Matches 🚀"):

    # validation
    if not biz_focus:
        st.warning("Please pick at least one Business / Business‑Focus.")
        st.stop()

    if "Please select" in [liquid_capital, hands_on_time, customer_type]:
        st.warning("Please complete all dropdowns.")
        st.stop()

    # -------- FILTER 1: BUSINESS FOCUS --------
    def row_matches_focus(industry_cell: str) -> bool:
        inds = [i.strip().lower() for i in str(industry_cell).split(",")]
        for bf in biz_focus:
            required_inds = [x.lower() for x in biz_map[bf]]
            if not any(req in ind for req in required_inds for ind in inds):
                return False
        return True

    df_f = df[df["industry"].apply(row_matches_focus)]

    if df_f.empty:
        st.error("No franchises matched the selected Business‑Focus categories.")
        st.stop()

    # -------- FILTER 2: FINANCIAL & OTHER --------
    cap_map = {"Under $50k": 50_000, "$50k-$99k": 99_000,
               "$100k-$249k": 249_000, "$250k+": 1_000_000}
    cap_limit = cap_map[liquid_capital] * (2 if finance else 1)

    df_f["cash required low"] = (
        df_f["cash required"].str.extract(r"(\d[\d,]*)")
                             .replace({",": ""}, regex=True)
                             .astype(float)
    )
    df_f = df_f[df_f["cash required low"] <= cap_limit]

    if hands_on_time == "5-20 hrs/week (semi-absentee)":
        df_f = df_f[df_f["semi-absentee ownership"] == "Yes"]
    elif hands_on_time == "<5 hrs/week (passive)":
        df_f = df_f[df_f["passive franchise"] == "Yes"]

    # optional extra industry filter
    if industry_interests:
        df_f = df_f[df_f["industry"].apply(
            lambda x: any(tag in str(x) for tag in industry_interests))
        ]

    if customer_type == "Businesses (B2B)":
        df_f = df_f[df_f["b2b"] == "Yes"]
    elif customer_type == "Consumers (B2C)":
        df_f = df_f[df_f["b2c"] == "Yes"]

    df_f = df_f.sort_values("industry_ranking")

    # fallback: keep business‑focus but ignore finance
    if df_f.empty:
        st.info("No brand met all filters. Showing top‑ranked brands that fit your "
                "Business‑Focus categories instead.")
        df_f = (df[df["industry"].apply(row_matches_focus)]
                .sort_values("industry_ranking"))

    top_n = df_f.head(RESULT_LIMIT)

    if top_n.empty:
        st.error("No franchises to display — please broaden your answers.")
        st.stop()

    # ---------- PRESENTATION ----------
    st.subheader(f"✨ Your Top {len(top_n)} Franchise Recommendations ✨")

    st.markdown("""
        <style>
          .rec {font-family: Helvetica, sans-serif; font-size: 16px; line-height: 1.45em;}
          .rec h3 {font-size: 24px; margin-bottom: 4px;}
        </style>
        """, unsafe_allow_html=True)

    def money(s):
        if s is None or pd.isna(s): return "contact us for details"
        s = re.sub(r"\s+", "", str(s)).replace("$$", "$")
        if not s.startswith("$"): s = "$" + s.lstrip("$")
        return s

    for _, row in top_n.iterrows():
        val = lambda c: row[c] if c in row and pd.notna(row[c]) else "contact us for details"
        brand = row["franchise name"]
        link  = f"[{brand}]({val('url')})" if val('url') != "contact us for details" else brand

        st.markdown('<div class="rec">', unsafe_allow_html=True)
        st.markdown(f"### {link}", unsafe_allow_html=True)
        st.markdown(f"**Industry:** {val('industry')}")
        st.markdown(f"**Description:** {val('business summary')}")
        st.markdown(f"**Startup Cost:** {money(row['cash required'])}")
        st.markdown(f"**Franchise Fee:** {money(val('franchise fee - one unit'))}")
        st.markdown(f"**Veteran Discount:** {val('veteran discount')}")
        st.markdown(f"**Industry Ranking:** {val('industry_ranking')}")
        st.markdown(f"**Number of Units Open:** {val('number of units open')}")
        st.markdown(f"**Support:** {val('support')}")
        st.markdown("</div><hr>", unsafe_allow_html=True)
