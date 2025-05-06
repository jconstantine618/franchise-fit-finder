import streamlit as st
import pandas as pd
import re, math
from pathlib import Path

# ---------- CONFIG ----------
DATA_FILE   = "ifpg_dataset.xlsx"              # IFPG master list
MAP_FILE    = "industry to business type.xlsx" # mapping sheet: business_type | industry
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

# helper → find the first column that starts with "franchise fee"
def get_fee_col(cols) -> str | None:
    for c in cols:
        if str(c).startswith("franchise fee"):
            return c
    return None

fee_col = get_fee_col(df.columns)     # may be None if not present
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

allowed_focus = [
    "professional services",
    "retail",
    "green & eco friendly",
    "health",
    "home and family",
]
map_df["business_type"] = map_df["business_type"].str.strip().str.lower()
map_df = map_df[map_df["business_type"].isin(allowed_focus)]

biz_map     = map_df.groupby("business_type")["industry"].apply(list).to_dict()
biz_options = sorted(biz_map.keys())
# ------------------------------------

# ---------- PAGE TITLE ----------
st.set_page_config(page_title="Franchise Fit Finder")
st.title("Franchise Fit Finder")
st.write("Answer the questions below to get your personalized franchise short‑list.")
# --------------------------------

# ---------- OPTIONAL CONTACT INFO ----------
st.text_input("Your Name (optional)")
st.text_input("Your Email (optional)")
st.text_input("Your Phone (optional)")
# ------------------------------------------

# ---------- BUSINESS‑FOCUS QUESTION ----------
biz_focus = st.multiselect(
    "Choose your preferred Focus *(pick up to 3)*",
    biz_options,
    max_selections=3,
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
    industry_tags,
