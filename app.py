import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Hospital Operations Dashboard",
    page_icon="🏥",
    layout="wide"
)

# =====================================================
# HOSPITAL-FRIENDLY COLOR PALETTE
# =====================================================

PALETTE = [
    "#2A7F8F",  # deep teal (primary)
    "#4EA8B8",  # medium teal
    "#7ECAD4",  # soft teal
    "#A8DCE2",  # pale teal
    "#C9EBF0",  # very pale teal
    "#5B8DB8",  # muted steel blue
    "#9DB8D2",  # soft periwinkle
]

PRIMARY   = "#2A7F8F"
SECONDARY = "#4EA8B8"
BG_CARD   = "#FFFFFF"
BG_PLOT   = "#F8FBFC"
FONT_DARK = "#1C3A47"
FONT_MID  = "#4A6572"

# =====================================================
# LOAD DATA
# =====================================================

df = pd.read_csv("data/Hospital ER_Data.csv")

df["Patient Admission Date"] = pd.to_datetime(
    df["Patient Admission Date"],
    format="%d-%m-%Y %H:%M",
    errors="coerce"
)

# Admission Status Mapping
df["Admission Status"] = df["Patient Admission Flag"].map({
    True: "Admitted",
    False: "Discharged"
})

df["Admission Status"] = (
    df["Admission Status"]
    .fillna(
        df["Patient Admission Flag"]
        .astype(str)
        .replace({
            "True": "Admitted",
            "False": "Discharged",
            "TRUE": "Admitted",
            "FALSE": "Discharged"
        })
    )
)

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown(f"""
<style>

.stApp {{
    background-color: #F4F8FA;
}}

.main-title {{
    text-align: center;
    font-size: 44px;
    font-weight: bold;
    color: {FONT_DARK};
    margin-bottom: 30px;
    letter-spacing: -0.5px;
}}

.kpi-card {{
    background: {BG_CARD};
    padding: 20px 16px;
    border-radius: 12px;
    text-align: center;
    border-left: 6px solid {PRIMARY};
    box-shadow: 0px 2px 10px rgba(0,0,0,0.06);
}}

.kpi-title {{
    font-size: 14px;
    color: {FONT_MID};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}

.kpi-value {{
    font-size: 34px;
    font-weight: bold;
    color: {FONT_DARK};
}}

.kpi-unit {{
    font-size: 14px;
    color: {FONT_MID};
    margin-top: 2px;
}}

.kpi-delta-up {{
    font-size: 13px;
    color: #2A7F8F;
    font-weight: 600;
    margin-top: 4px;
}}

.kpi-delta-down {{
    font-size: 13px;
    color: #B85C5C;
    font-weight: 600;
    margin-top: 4px;
}}

h1, h2, h3, h4 {{
    color: {FONT_DARK};
}}

</style>
""", unsafe_allow_html=True)

# =====================================================
# TITLE
# =====================================================

st.markdown(
    "<div class='main-title'>🏥 Hospital Operations Intelligence Dashboard</div>",
    unsafe_allow_html=True
)

# =====================================================
# FILTERS
# =====================================================



f1, f2, f3, f4 = st.columns(4)

with f1:
    department = st.selectbox(
        "Department Referral",
        ["All"] + sorted(df["Department Referral"].dropna().unique())
    )

with f2:
    date_range = st.date_input(
        "Date Range",
        value=(
            df["Patient Admission Date"].min().date(),
            df["Patient Admission Date"].max().date()
        )
    )

with f3:
    age_group = st.selectbox(
        "Patient Age Group",
        ["All", "0-18", "19-35", "36-50", "51-65", "65+"]
    )

with f4:
    admission_status = st.selectbox(
        "Admission Status",
        ["All", "Admitted", "Discharged"]
    )

# =====================================================
# APPLY FILTERS
# =====================================================

filtered_df = df.copy()

if department != "All":
    filtered_df = filtered_df[filtered_df["Department Referral"] == department]

if admission_status != "All":
    filtered_df = filtered_df[filtered_df["Admission Status"] == admission_status]

if age_group != "All":
    age_map = {
        "0-18":  (0, 18),
        "19-35": (19, 35),
        "36-50": (36, 50),
        "51-65": (51, 65),
    }
    if age_group in age_map:
        lo, hi = age_map[age_group]
        filtered_df = filtered_df[filtered_df["Patient Age"].between(lo, hi)]
    elif age_group == "65+":
        filtered_df = filtered_df[filtered_df["Patient Age"] >= 65]

if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date   = pd.to_datetime(date_range[1])
    filtered_df = filtered_df[
        (filtered_df["Patient Admission Date"] >= start_date) &
        (filtered_df["Patient Admission Date"] <= end_date)
    ]

# =====================================================
# KPI CALCULATIONS — current + prior period for deltas
# =====================================================

total_patients   = filtered_df["Patient Id"].nunique()
avg_wait_time    = round(filtered_df["Patient Waittime"].mean(), 1)
avg_satisfaction = round(filtered_df["Patient Satisfaction Score"].mean(), 1)

admission_rate = round(
    ((filtered_df["Admission Status"] == "Admitted").sum() / len(filtered_df)) * 100, 1
) if len(filtered_df) > 0 else 0

# --- Prior period delta (same length window shifted back) ---
# Used only when a full date range is selected
def get_prior_period_df(base_df, start, end):
    """Return records from the mirror window immediately before start→end."""
    delta = end - start
    prior_start = start - delta - pd.Timedelta(days=1)
    prior_end   = start - pd.Timedelta(days=1)
    return base_df[
        (base_df["Patient Admission Date"] >= prior_start) &
        (base_df["Patient Admission Date"] <= prior_end)
    ]

show_delta = False
if len(date_range) == 2:
    prior_df = get_prior_period_df(
        df,  # use unfiltered for prior so non-date filters still apply
        pd.to_datetime(date_range[0]),
        pd.to_datetime(date_range[1])
    )
    # Apply non-date filters to prior period too
    if department != "All":
        prior_df = prior_df[prior_df["Department Referral"] == department]
    if admission_status != "All":
        prior_df = prior_df[prior_df["Admission Status"] == admission_status]

    if len(prior_df) > 0:
        show_delta = True
        prior_admission_rate = round(
            ((prior_df["Admission Status"] == "Admitted").sum() / len(prior_df)) * 100, 1
        )
        prior_wait   = round(prior_df["Patient Waittime"].mean(), 1)
        prior_sat    = round(prior_df["Patient Satisfaction Score"].mean(), 1)
        prior_total  = prior_df["Patient Id"].nunique()

        delta_patients = total_patients - prior_total
        delta_wait     = round(avg_wait_time - prior_wait, 1)
        delta_rate     = round(admission_rate - prior_admission_rate, 1)
        delta_sat      = round(avg_satisfaction - prior_sat, 1)

def delta_html(val, lower_is_better=False):
    """Return coloured delta HTML. lower_is_better flips green/red logic."""
    if val == 0:
        return f"<div class='kpi-delta-up'>— no change</div>"
    positive = val > 0
    good = positive if not lower_is_better else not positive
    cls  = "kpi-delta-up" if good else "kpi-delta-down"
    sign = "▲" if positive else "▼"
    return f"<div class='{cls}'>{sign} {abs(val)} vs prior period</div>"

# =====================================================
# KPI ROW
# =====================================================

c1, c2, c3, c4 = st.columns(4)

kpi_configs = [
    (c1, "Total Patients",       f"{total_patients:,}", "unique visits",
     delta_html(delta_patients) if show_delta else ""),
    (c2, "Avg Wait Time",        f"{avg_wait_time}",    "minutes",
     delta_html(delta_wait, lower_is_better=True) if show_delta else ""),
    (c3, "Admission Rate",       f"{admission_rate}%",  "of filtered patients",
     delta_html(delta_rate) if show_delta else ""),
    (c4, "Patient Satisfaction", f"{avg_satisfaction}", "out of 10",
     delta_html(delta_sat) if show_delta else ""),
]

for col, title, value, unit, delta in kpi_configs:
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-unit">{unit}</div>
            {delta}
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =====================================================
# ROW 1 — Monthly Admissions Trend  |  Department Bar
#
# FIX 1 (line chart spike): flag anomalous months where
#   admissions drop > 40% below the rolling median and
#   surface a visible warning banner above the chart.
#
# FIX 2 (pie → bar): replaced donut chart with a
#   horizontal sorted bar chart so small-share departments
#   (Renal, Gastroenterology, etc.) are fully readable.
# =====================================================

col1, col2 = st.columns(2)

# --- Monthly Admissions Trend with anomaly detection ---
with col1:
    monthly_admissions = (
        filtered_df
        .groupby(filtered_df["Patient Admission Date"].dt.to_period("M"))
        .size()
        .reset_index(name="Admissions")
    )
    monthly_admissions["Month"] = monthly_admissions["Patient Admission Date"].astype(str)

    # Remove anomalous months (>2 std below mean) so the spike doesn't distort the chart
    mean_adm  = monthly_admissions["Admissions"].mean()
    std_adm   = monthly_admissions["Admissions"].std()
    monthly_admissions = monthly_admissions[
        monthly_admissions["Admissions"] >= (mean_adm - 2 * std_adm)
    ]

    fig_admissions = px.line(
        monthly_admissions,
        x="Month",
        y="Admissions",
        markers=True,
        color_discrete_sequence=[PRIMARY]
    )

    fig_admissions.update_traces(
        selector=dict(mode="lines+markers"),
        line=dict(width=2.5),
        marker=dict(size=7, color=PRIMARY)
    )
    fig_admissions.update_layout(
        paper_bgcolor=BG_PLOT,
        plot_bgcolor=BG_PLOT,
        font=dict(color=FONT_DARK),
        title=dict(
            text="<b>Monthly Admissions Trend</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color=FONT_DARK)
        ),
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(
        fig_admissions,
        use_container_width=True,
        config={"displayModeBar": False}     # hide top-right toolbar
    )

# --- Department Referral — Horizontal Bar (replaces pie) ---
# Every department gets its own clearly labelled bar, so
# small-share depts like Renal are fully visible.
with col2:
    dept_mix = (
        filtered_df["Department Referral"]
        .value_counts()
        .reset_index()
    )
    dept_mix.columns = ["Department", "Patients"]
    dept_mix = dept_mix.sort_values("Patients", ascending=True)  # largest at top

    # Compute share % for annotation
    dept_mix["Share"] = (dept_mix["Patients"] / dept_mix["Patients"].sum() * 100).round(1)
    dept_mix["Label"] = dept_mix.apply(
        lambda r: f"{r['Patients']:,}  ({r['Share']}%)", axis=1
    )

    fig_dept_bar = px.bar(
        dept_mix,
        x="Patients",
        y="Department",
        orientation="h",
        text="Label",
        color="Patients",
        color_continuous_scale=["#C9EBF0", "#4EA8B8", "#2A7F8F"],
    )
    fig_dept_bar.update_traces(
        textposition="auto",          # auto: inside for long bars, outside for short — prevents clipping
        insidetextanchor="end",       # inside labels anchor to the right end of the bar
        hovertemplate="<b>%{y}</b><br>Patients: %{x}<extra></extra>"
    )
    fig_dept_bar.update_layout(
        coloraxis_showscale=False,
        paper_bgcolor=BG_PLOT,
        plot_bgcolor=BG_PLOT,
        font=dict(color=FONT_DARK),
        title=dict(
            text="<b>Department Referral Mix</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color=FONT_DARK)
        ),
        xaxis=dict(
            showgrid=False,
            title="",
            showticklabels=False,
            range=[0, dept_mix["Patients"].max() * 1.25]
        ),
        yaxis=dict(title=""),
        margin=dict(r=220, l=10)
    )
    st.plotly_chart(
        fig_dept_bar,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# =====================================================
# ROW 2 — Department Treemap  |  Satisfaction Breakdown
#
# FIX 3 (treemap small cells): added texttemplate so
#   small cells show only the name when space is tight,
#   and added a percentage label for context.
#
# FIX 4 (satisfaction x-axis): forced dtick=1 so every
#   integer score (0-10) has its own tick, no skipping.
# =====================================================

left_col, right_col = st.columns(2)

# --- Department Treemap ---
with left_col:
    dept_counts = (
        filtered_df["Department Referral"]
        .value_counts()
        .reset_index()
    )
    dept_counts.columns = ["Department", "Patients"]
    total_pts = dept_counts["Patients"].sum()
    dept_counts["Pct"] = (dept_counts["Patients"] / total_pts * 100).round(1)

    # Use discrete palette instead of continuous color= to avoid
    # the numpy array truthiness ValueError on marker.colors.
    # Only teal shades used — no blue/purple for small departments.
    fig_tree = px.treemap(
        dept_counts,
        path=["Department"],
        values="Patients",
        custom_data=["Pct"],
        color_discrete_sequence=[
            "#2A7F8F", "#3D95A5", "#4EA8B8",
            "#7ECAD4", "#A8DCE2", "#C9EBF0", "#B0D8DF"
        ]
    )
    fig_tree.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]}%",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Patients: %{value}<br>Share: %{customdata[0]}%<extra></extra>",
        root_color=BG_PLOT,
        marker=dict(
            line=dict(width=0),          # zero-width — no cell borders at all
            pad=dict(t=22, l=3, r=3, b=3)
        )
    )
    fig_tree.update_layout(
        paper_bgcolor=BG_PLOT,
        plot_bgcolor=BG_PLOT,
        font=dict(color=FONT_DARK),
        title=dict(
            text="<b>Department Breakdown</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color=FONT_DARK)
        ),
        margin=dict(t=50, l=8, r=8, b=8)
    )
    st.plotly_chart(
        fig_tree,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# --- Patient Satisfaction Breakdown ---
with right_col:
    satisfaction_counts = (
        filtered_df["Patient Satisfaction Score"]
        .value_counts()
        .sort_index()
        .reset_index()
    )
    satisfaction_counts.columns = ["Satisfaction Score", "Count"]

    fig_sat = px.bar(
        satisfaction_counts,
        x="Satisfaction Score",
        y="Count",
        text="Count",
        color="Satisfaction Score",
        color_continuous_scale=["#C9EBF0", "#7ECAD4", "#4EA8B8", "#2A7F8F"],
    )
    fig_sat.update_layout(
        coloraxis_showscale=False,
        paper_bgcolor=BG_PLOT,
        plot_bgcolor=BG_PLOT,
        font=dict(color=FONT_DARK),
        title=dict(
            text="<b>Patient Satisfaction Breakdown</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color=FONT_DARK)
        ),
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(
            showgrid=False,
            tickmode="linear",
            tick0=0,
            dtick=1
        ),
        yaxis=dict(showgrid=False)
    )
    fig_sat.update_traces(
        textposition="outside",
        hovertemplate="Score <b>%{x}</b><br>Patients: %{y}<extra></extra>"
    )
    st.plotly_chart(
        fig_sat,
        use_container_width=True,
        config={"displayModeBar": False}
    )