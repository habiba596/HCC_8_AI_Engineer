import streamlit as st
import os
from query_graph import graph

st.set_page_config(
    page_title="Sky Agenda",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    [data-testid="stHeader"] {
        background-color: transparent !important;
        color: transparent !important;
    }

    .stApp {
        background-color: #B6B8AD !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    ::selection {
        background: #B6B8AD !important;
        color: #782318 !important;
    }

    .block-container {
        max-width: 1000px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }

    .main-title {
        color: #782318 !important;
        text-align: center;
        font-size: 3.4rem !important;
        font-weight: 900;
        margin-top: 5px;
        margin-bottom: 5px;
    }

    .page-desc {
        color: #782318 !important;
        text-align: center;
        font-size: 1.35rem !important;
        font-weight: 700;
        margin-bottom: 25px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #84782B !important;
        border: 2px solid #84782B !important;
        border-radius: 14px !important;
        padding: 18px !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
    }

    .stTextInput label, .stSelectbox label,
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] span,
    label p {
        color: #782318 !important;
        font-weight: 700 !important;
        font-size: 1.25rem !important;
    }

    .stTextInput input {
        background-color: #ffffff !important;
        color: #782318 !important;
        border: 1px solid #782318 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1.15rem !important;
        height: 50px !important;
    }

    .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #782318 !important;
        border: 1px solid #782318 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1.15rem !important;
        min-height: 50px !important;
    }

    .stSelectbox div[data-baseweb="select"] * {
        color: #782318 !important;
    }

    .stTextInput input::placeholder {
        color: rgba(120, 35, 24, 0.75) !important;
    }

    .stSelectbox svg {
        fill: #782318 !important;
        width: 26px !important;
        height: 26px !important;
    }

    .stButton > button {
        background-color: #782318 !important;
        color: #B6B8AD !important;
        border: 2px solid #782318 !important;
        border-radius: 10px !important;
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        padding: 12px 20px !important;
        width: 100% !important;
        margin-top: 10px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 5px 12px rgba(0,0,0,0.15) !important;
    }

    .stButton > button:hover {
        background-color: #B09E31 !important;
        color: #782318 !important;
        border: 2px solid #B09E31 !important;
        cursor: pointer;
    }

    .output-box {
        background-color: #782318 !important;
        border: 2px solid #B09E31 !important;
        border-radius: 14px;
        padding: 22px;
        color: #B6B8AD !important;
        font-size: 1.25rem !important;
        line-height: 1.7;
        margin-top: 25px;
        direction: rtl;
        text-align: right;
    }

    .output-box, .output-box * {
        color: #B6B8AD !important;
    }

    .error-box {
        background-color: #AF2920 !important;
        border: 2px solid #B6B8AD !important;
        border-radius: 14px;
        padding: 22px;
        color: #B6B8AD !important;
        font-size: 1.15rem !important;
        line-height: 1.7;
        margin-top: 25px;
        direction: rtl;
        text-align: right;
    }

    .error-box, .error-box * {
        color: #B6B8AD !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Sky Agenda</div>', unsafe_allow_html=True)
st.markdown('<div class="page-desc">Your personal assistant for discovering celestial and astronomical events</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        location = st.text_input(
            "Location",
            placeholder="e.g. مصر / Cairo",
            key="location_input"
        )

with col2:
    with st.container(border=True):
        period = st.selectbox(
            "Time Period",
            options=[
                "Whole Year",
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
                "Spring", "Summer", "Autumn", "Winter"
            ],
            key="period_input"
        )

col3, col4 = st.columns(2)

with col3:
    with st.container(border=True):
        direction = st.selectbox(
            "Viewing Direction",
            options=["Any Direction", "الشرق", "الغرب", "الشمال", "الجنوب"],
            key="direction_input"
        )

with col4:
    with st.container(border=True):
        language = st.selectbox(
            "Response Language",
            options=["العربية", "English"],
            key="language_input"
        )

st.markdown("<br>", unsafe_allow_html=True)

submit_button = st.button("Submit Question", use_container_width=True)

if submit_button:
    with st.spinner("Processing astronomical request..."):
        try:
            user_period_str = period if period != "Whole Year" else "كل السنة"
            user_dir_str = direction if direction != "Any Direction" else ""

            result = graph.invoke({
                "userLocation": location.strip(),
                "userPeriod": user_period_str,
                "userDirection": user_dir_str,
                "userLanguage": language
            })

            friendly_answer = result.get("friendlyAnswer", "No data returned.")

            st.markdown(f'''
            <div class="output-box">
                {friendly_answer}
            </div>
            ''', unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f'''
            <div class="error-box">
                An error occurred while connecting to the backend: {str(e)}
            </div>
            ''', unsafe_allow_html=True)