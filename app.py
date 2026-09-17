
import itertools
import math
from datetime import datetime

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="CHIPSHIELD — Cascade Resilience",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / helpers
# -----------------------------
st.markdown("""
<style>
/* CHIPSHIELD — matte premium UI */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: "DM Sans", system-ui, sans-serif;
}
.stApp {
    background: #0b0d0f;
    color: #e8e8e5;
}
.block-container {
    max-width: 1320px;
    padding-top: 2rem;
    padding-bottom: 2.5rem;
}
[data-testid="stSidebar"] {
    background: #0e1012;
    border-right: 1px solid #202326;
}
[data-testid="stSidebar"] * {
    color: #d9dbd8;
}
.hero {
    font-family: "Manrope", sans-serif;
    font-size: 3.35rem;
    font-weight: 800;
    letter-spacing: -.065em;
    line-height: .95;
    margin: .15rem 0 .45rem;
    color: #f0f0ed;
}
.kicker {
    color: #8f9793;
    font-size: .69rem;
    letter-spacing: .16em;
    font-weight: 700;
    text-transform: uppercase;
}
.sub {
    color: #8e9591;
    font-size: .94rem;
    max-width: 760px;
    line-height: 1.6;
}
.card {
    background: #111416;
    border: 1px solid #22272a;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 28px rgba(0,0,0,.16);
}
.card h3 {
    font-family: "Manrope", sans-serif;
    font-size: .82rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #9ba19e;
    margin-top: 0;
}
[data-testid="stMetric"] {
    background: #111416;
    border: 1px solid #22272a;
    border-radius: 14px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] {
    color: #777f7b;
}
[data-testid="stMetricValue"] {
    color: #e9ebe8;
}
.stButton > button {
    border-radius: 10px;
    min-height: 44px;
    font-weight: 700;
    border: 1px solid #303538;
}
.stButton > button[kind="primary"] {
    background: #e8e9e6;
    color: #101214;
    border: 0;
}
.stButton > button[kind="primary"]:hover {
    background: #ffffff;
    color: #101214;
}
.stSelectbox, .stSlider {
    margin-bottom: .35rem;
}
div[data-baseweb="select"] > div {
    background: #111416;
    border-color: #2a2e31;
    border-radius: 10px;
}
[data-testid="stExpander"] {
    background: #111416;
    border: 1px solid #22272a;
    border-radius: 12px;
}
[data-testid="stDataFrame"] {
    border: 1px solid #22272a;
    border-radius: 12px;
    overflow: hidden;
}
.modelled {
    border: 1px solid #2b3433;
    background: #101817;
    padding: 9px 12px;
    border-radius: 9px;
    color: #a9b8b3;
    font-size: .76rem;
}
.small {
    color: #737b77;
    font-size: .76rem;
    line-height: 1.55;
}
.section-label {
    color: #777f7b;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: .45rem;
}
.status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    margin-right: 7px;
}
hr {
    border-color: #202427;
}
h1, h2, h3 {
    font-family: "Manrope", sans-serif;
}
h1 {
    letter-spacing: -.045em;
}
</style>
""", unsafe_allow_html=True)

RESOURCES = ["Water", "Power", "Chemicals", "Logistics"]
RESOURCE_ICONS = {"Water":"💧", "Power":"⚡", "Chemicals":"🧪", "Logistics":"🚚"}
RESOURCE_COLORS = {"Water":"#45b8ff", "Power":"#ffd166", "Chemicals":"#c084fc", "Logistics":"#8be28b"}

DEFAULTS = {
    "water_buffer": 3.0,
    "power_redundancy": 20.0,
    "chemical_redundancy": 10.0,
    "logistics_buffer": 5.0,
}

INTERVENTIONS = pd.DataFrame([
    ["Water recycling", "Water", 25, "buffer_days", 5.0, "Adds 5 days of effective water resilience."],
    ["Power backup", "Power", 20, "redundancy", 25.0, "Adds 25 percentage points of power redundancy."],
    ["Chemical redundancy", "Chemicals", 12, "redundancy", 30.0, "Adds 30 percentage points of chemical redundancy."],
    ["Inventory buffer", "Logistics", 8, "buffer_days", 7.0, "Adds 7 days of logistics buffer."],
], columns=["Intervention","Resource","Cost (Cr)","Type","Effect","Description"])


def status_from_factor(x):
    if x >= 0.85:
        return "Normal", "#35d07f"
    if x >= 0.60:
        return "At risk", "#f4c95d"
    return "Critical", "#ff5d73"


def build_graph():
    G = nx.DiGraph()
    G.add_nodes_from([
        "Water", "Power", "Chemicals", "Dholera Fab", "Chip Output",
        "Automotive", "Consumer", "Industrial"
    ])
    G.add_edges_from([
        ("Water","Dholera Fab"), ("Power","Dholera Fab"),
        ("Chemicals","Dholera Fab"), ("Dholera Fab","Chip Output"),
        ("Chip Output","Automotive"), ("Chip Output","Consumer"),
        ("Chip Output","Industrial"),
    ])
    return G


def effective_resource_availability(resource, reduction, duration, assumptions):
    """
    Transparent illustrative model.

    Buffer is treated as protected full-supply days.
    Redundancy reduces the portion of the disruption that becomes effective.
    The result is an average availability factor over the disruption window.
    """
    buffer = assumptions["buffers"].get(resource, 0.0)
    redundancy = assumptions["redundancy"].get(resource, 0.0) / 100.0

    effective_reduction = reduction * (1.0 - redundancy)
    protected_days = min(duration, buffer)
    exposed_days = max(0.0, duration - protected_days)

    avg_availability = (
        protected_days * 1.0 + exposed_days * (1.0 - effective_reduction)
    ) / max(duration, 1.0)

    return max(0.0, min(1.0, avg_availability))


def simulate(failure_type, reduction_pct, duration_days, assumptions):
    reduction = reduction_pct / 100.0
    resource_factors = {r: 1.0 for r in RESOURCES}
    resource_factors[failure_type] = effective_resource_availability(
        failure_type, reduction, duration_days, assumptions
    )

    # Bottleneck model: fab throughput is constrained by the tightest input.
    fab_output = min(resource_factors.values())
    chip_output = fab_output

    downstream_exposure = {
        "Automotive": chip_output,
        "Consumer": 0.55 + 0.45 * chip_output,
        "Industrial": 0.85 * chip_output + 0.15,
    }

    production_loss = 1.0 - fab_output
    recovery_days = (
        2.0
        + 0.25 * duration_days
        + 8.0 * max(0.0, 0.80 - fab_output)
    )

    return {
        "resource_factors": resource_factors,
        "fab_output": fab_output,
        "chip_output": chip_output,
        "production_loss": production_loss,
        "recovery_days": round(recovery_days, 1),
        "downstream": downstream_exposure,
    }


def apply_portfolio(base_assumptions, selected_names):
    a = {
        "buffers": dict(base_assumptions["buffers"]),
        "redundancy": dict(base_assumptions["redundancy"]),
    }
    for name in selected_names:
        row = INTERVENTIONS[INTERVENTIONS["Intervention"] == name].iloc[0]
        resource = row["Resource"]
        if row["Type"] == "buffer_days":
            a["buffers"][resource] += float(row["Effect"])
        else:
            a["redundancy"][resource] += float(row["Effect"])
    return a


def optimize(failure_type, reduction_pct, duration_days, base_assumptions, budget=50):
    rows = []
    names = INTERVENTIONS["Intervention"].tolist()

    baseline = simulate(failure_type, reduction_pct, duration_days, base_assumptions)
    baseline_loss = baseline["production_loss"]

    for n in range(len(names) + 1):
        for combo in itertools.combinations(names, n):
            total_cost = int(INTERVENTIONS[INTERVENTIONS["Intervention"].isin(combo)]["Cost (Cr)"].sum())
            if total_cost > budget:
                continue
            assumptions = apply_portfolio(base_assumptions, combo)
            result = simulate(failure_type, reduction_pct, duration_days, assumptions)
            avoided = baseline_loss - result["production_loss"]
            rows.append({
                "Portfolio": " + ".join(combo) if combo else "No intervention",
                "Cost (Cr)": total_cost,
                "Production loss": result["production_loss"],
                "Production loss avoided": avoided,
                "Fab output": result["fab_output"],
                "Recovery (days)": result["recovery_days"],
            })

    df = pd.DataFrame(rows)
    # Primary objective = production loss avoided. Tie-breakers: lower cost, lower recovery.
    df = df.sort_values(
        ["Production loss avoided", "Cost (Cr)", "Recovery (days)"],
        ascending=[False, True, True]
    ).reset_index(drop=True)
    return df, baseline


def network_figure(result=None):
    G = build_graph()
    pos = {
        "Water": (0, 2), "Power": (0, 1), "Chemicals": (0, 0),
        "Dholera Fab": (1.5, 1), "Chip Output": (3, 1),
        "Automotive": (4.7, 2), "Consumer": (4.7, 1), "Industrial": (4.7, 0)
    }

    factors = {n: 1.0 for n in G.nodes}
    if result:
        for r, v in result["resource_factors"].items():
            factors[r] = v
        factors["Dholera Fab"] = result["fab_output"]
        factors["Chip Output"] = result["chip_output"]
        for k, v in result["downstream"].items():
            factors[k] = v

    node_colors = []
    node_sizes = []
    labels = []
    for n in G.nodes:
        _, c = status_from_factor(factors[n])
        node_colors.append(c)
        node_sizes.append(30 if n in ["Dholera Fab","Chip Output"] else 23)
        labels.append(f"{RESOURCE_ICONS.get(n,'🏭')} {n}")

    edge_x, edge_y = [], []
    for u, v in G.edges:
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=2, color="#3b4a60"),
        hoverinfo="none"
    )

    node_trace = go.Scatter(
        x=[pos[n][0] for n in G.nodes],
        y=[pos[n][1] for n in G.nodes],
        mode="markers+text",
        text=labels,
        textposition="middle center",
        textfont=dict(size=12, color="#f4f7fb"),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="#0a1019")
        ),
        customdata=[
            f"Availability: {factors[n]*100:.1f}% | {status_from_factor(factors[n])[0]}"
            for n in G.nodes
        ],
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        height=470,
        margin=dict(l=10,r=10,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False, range=[-0.5,5.3]),
        yaxis=dict(visible=False, range=[-0.6,2.6]),
        font=dict(color="#eef3f8"),
    )
    return fig


def impact_bar(result):
    labels = ["Automotive", "Consumer", "Industrial"]
    values = [result["downstream"][x] * 100 for x in labels]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=["#ff8a9a" if v < 65 else "#f4c95d" if v < 85 else "#35d07f" for v in values]),
        text=[f"{v:.1f}% capacity" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20,r=50,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0,105], title="Modelled remaining capacity (%)"),
        yaxis=dict(autorange="reversed"),
        font=dict(color="#dbe4ee"),
    )
    return fig


def assumptions_from_session():
    return {
        "buffers": {
            "Water": st.session_state.water_buffer,
            "Power": 0.0,
            "Chemicals": 0.0,
            "Logistics": st.session_state.logistics_buffer,
        },
        "redundancy": {
            "Water": 0.0,
            "Power": st.session_state.power_redundancy,
            "Chemicals": st.session_state.chemical_redundancy,
            "Logistics": 0.0,
        },
    }


# -----------------------------
# Sidebar controls
# -----------------------------
if "water_buffer" not in st.session_state:
    st.session_state.water_buffer = DEFAULTS["water_buffer"]
if "power_redundancy" not in st.session_state:
    st.session_state.power_redundancy = DEFAULTS["power_redundancy"]
if "chemical_redundancy" not in st.session_state:
    st.session_state.chemical_redundancy = DEFAULTS["chemical_redundancy"]
if "logistics_buffer" not in st.session_state:
    st.session_state.logistics_buffer = DEFAULTS["logistics_buffer"]

st.sidebar.markdown("## CHIPSHIELD")
st.sidebar.caption("Cascade resilience")

page = st.sidebar.radio(
    "Navigate",
    ["01 · Overview", "02 · Create Failure", "03 · Cascade Impact", "04 · Resilience Optimizer"],
)

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Assumptions", expanded=True):
    st.session_state.water_buffer = st.slider("Water buffer (days)", 0.0, 14.0, float(st.session_state.water_buffer), 0.5)
    st.session_state.power_redundancy = st.slider("Power redundancy (%)", 0.0, 60.0, float(st.session_state.power_redundancy), 5.0)
    st.session_state.chemical_redundancy = st.slider("Chemical redundancy (%)", 0.0, 60.0, float(st.session_state.chemical_redundancy), 5.0)
    st.session_state.logistics_buffer = st.slider("Logistics buffer (days)", 0.0, 14.0, float(st.session_state.logistics_buffer), 0.5)
    st.caption("Illustrative engineering assumptions — not Tata Electronics operational data.")

st.sidebar.markdown("---")
st.sidebar.caption("MODELLED RESULT — NOT A FORECAST")
st.sidebar.caption("MVP uses a transparent bottleneck + buffer model.")

assumptions = assumptions_from_session()

# -----------------------------
# Screen 1
# -----------------------------
if page == "01 · Overview":
    st.markdown('<div class="kicker">CRITICAL INFRASTRUCTURE · SEMICONDUCTOR SUPPLY CHAIN</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero">CHIPSHIELD</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub"><b>See the failure before the shortage.</b> Simulate infrastructure disruption, trace the cascade, and test resilience investments.</div>', unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns([1.65, 1])
    with c1:
        st.markdown('<div class="card"><h3>DHOLERA FAB — DEPENDENCY MAP</h3>', unsafe_allow_html=True)
        st.plotly_chart(network_figure(), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><h3>PUBLIC PROJECT CONTEXT</h3>', unsafe_allow_html=True)
        facts = [
            ("Investment", "Up to ₹91,000 Cr"),
            ("Capacity", "Up to 50,000 wafers/month"),
            ("Technology", "28 nm to 110 nm"),
            ("Technology partner", "PSMC"),
            ("Location", "Dholera, Gujarat"),
            ("Status", "Under development"),
        ]
        for k,v in facts:
            st.markdown(f"**{k}**  \n{v}")
            st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="small">Public project facts are separate from the illustrative simulation.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="modelled">MODELLED RESULT — NOT A FORECAST · The simulation uses stated illustrative assumptions rather than proprietary production, supplier, inventory or infrastructure data.</div>', unsafe_allow_html=True)

# -----------------------------
# Screen 2
# -----------------------------
elif page == "02 · Create Failure":
    st.markdown('<div class="kicker">SCENARIO BUILDER</div>', unsafe_allow_html=True)
    st.title("Create a failure")
    st.write("Set one disruption. The model calculates the resulting bottleneck.")

    left, right = st.columns([1, 1.4])
    with left:
        failure_type = st.selectbox("Failure type", RESOURCES, format_func=lambda x: f"{RESOURCE_ICONS[x]}  {x}")
        reduction_pct = st.slider("Supply reduction", 0, 100, 50, 5)
        duration_days = st.slider("Duration", 1, 30, 7, 1)

        st.markdown("### Scenario")
        st.code(f"""Failure:
{failure_type} supply ↓ {reduction_pct}%

Duration:
{duration_days} days""")

        if st.button("⚡ SIMULATE CASCADE", type="primary", use_container_width=True):
            st.session_state.failure_type = failure_type
            st.session_state.reduction_pct = reduction_pct
            st.session_state.duration_days = duration_days
            st.session_state.result = simulate(failure_type, reduction_pct, duration_days, assumptions)
            st.session_state.simulated = True

    with right:
        st.markdown('<div class="card"><h3>MODEL LOGIC</h3>', unsafe_allow_html=True)
        st.markdown("""
**Disruption → bottleneck → downstream impact.**

Buffers and redundancy absorb part of the shock. The tightest resource constrains fab output, which then propagates to chip-dependent sectors.

<div class="small">Transparent scenario model; no proprietary fab data.</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("simulated"):
        st.success("Scenario created. Open **03 · Cascade Impact** to inspect the propagation.")
        r = st.session_state.result
        st.metric("Modelled fab output", f"{r['fab_output']*100:.1f}%")
        st.metric("Modelled production loss", f"{r['production_loss']*100:.1f}%")

# -----------------------------
# Screen 3
# -----------------------------
elif page == "03 · Cascade Impact":
    st.markdown('<div class="kicker">CASCADE ENGINE</div>', unsafe_allow_html=True)
    st.title("Cascade impact")

    if not st.session_state.get("simulated"):
        st.info("Create a scenario on Screen 2 first.")
        st.stop()

    result = st.session_state.result
    failure_type = st.session_state.failure_type
    reduction_pct = st.session_state.reduction_pct
    duration_days = st.session_state.duration_days

    st.markdown(
        f'<div class="modelled">MODELLED RESULT — NOT A FORECAST · {failure_type} reduction {reduction_pct}% for {duration_days} days.</div>',
        unsafe_allow_html=True
    )
    st.write("")

    st.plotly_chart(network_figure(result), use_container_width=True, config={"displayModeBar": False})

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fab production impact", f"-{result['production_loss']*100:.1f}%")
    m2.metric("Chip output", f"{result['chip_output']*100:.1f}%")
    m3.metric("Recovery time", f"{result['recovery_days']:.1f} days")
    bottleneck = min(result["resource_factors"], key=result["resource_factors"].get)
    m4.metric("Bottleneck", bottleneck)

    st.write("")
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("### Resource state")
        resource_df = pd.DataFrame([
            {
                "Infrastructure": r,
                "Modelled availability": result["resource_factors"][r] * 100,
                "Status": status_from_factor(result["resource_factors"][r])[0],
            }
            for r in RESOURCES
        ])
        resource_df["Modelled availability"] = resource_df["Modelled availability"].map(lambda x: f"{x:.1f}%")
        st.dataframe(resource_df, hide_index=True, use_container_width=True)

    with right:
        st.markdown("### Downstream exposure")
        st.plotly_chart(impact_bar(result), use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Why the cascade occurs")
    st.write(
        f"The selected disruption reduces {failure_type.lower()} availability. "
        f"The fab is constrained by the lowest effective resource availability, which is **{bottleneck.lower()}** "
        f"at {result['resource_factors'][bottleneck]*100:.1f}%. That constraint is passed to chip output and then translated into downstream exposure."
    )

# -----------------------------
# Screen 4
# -----------------------------
else:
    st.markdown('<div class="kicker">RESILIENCE OPTIMIZER</div>', unsafe_allow_html=True)
    st.title("Where should ₹50 crore go?")
    st.write("Test every feasible resilience portfolio within the ₹50 Cr budget.")

    if not st.session_state.get("simulated"):
        st.info("Create a failure scenario on Screen 2 first.")
        st.stop()

    failure_type = st.session_state.failure_type
    reduction_pct = st.session_state.reduction_pct
    duration_days = st.session_state.duration_days

    opt_df, baseline = optimize(
        failure_type, reduction_pct, duration_days, assumptions, budget=50
    )
    best = opt_df.iloc[0]

    st.markdown('<div class="modelled">MODELLED RESULT — BASED ON STATED ASSUMPTIONS · Portfolio selection maximises modelled production loss avoided within ₹50 Cr.</div>', unsafe_allow_html=True)
    st.write("")

    c1,c2,c3 = st.columns(3)
    c1.metric("Budget", "₹50 Cr")
    c2.metric("Baseline production loss", f"{baseline['production_loss']*100:.1f}%")
    c3.metric("Best modelled loss avoided", f"{best['Production loss avoided']*100:.1f}%")

    st.write("")
    st.markdown("### Recommended portfolio")
    portfolio_names = [x.strip() for x in str(best["Portfolio"]).split(" + ")] if best["Portfolio"] != "No intervention" else []
    if portfolio_names:
        portfolio_table = INTERVENTIONS[INTERVENTIONS["Intervention"].isin(portfolio_names)][["Intervention","Resource","Cost (Cr)","Description"]].copy()
        st.dataframe(portfolio_table, hide_index=True, use_container_width=True)
    else:
        st.write("No intervention is selected under the current scenario and assumptions.")

    a,b,c,d = st.columns(4)
    a.metric("Total investment", f"₹{best['Cost (Cr)']} Cr")
    b.metric("Remaining budget", f"₹{50-best['Cost (Cr)']} Cr")
    c.metric("Fab output after", f"{best['Fab output']*100:.1f}%")
    d.metric("Recovery after", f"{best['Recovery (days)']:.1f} days")

    st.write("")
    st.markdown("### All feasible portfolios")
    display = opt_df.copy()
    display["Production loss avoided"] = (display["Production loss avoided"]*100).map(lambda x: f"{x:.1f}%")
    display["Production loss"] = (display["Production loss"]*100).map(lambda x: f"{x:.1f}%")
    display["Fab output"] = (display["Fab output"]*100).map(lambda x: f"{x:.1f}%")
    display["Recovery (days)"] = display["Recovery (days)"].map(lambda x: f"{x:.1f}")
    st.dataframe(display.head(10), hide_index=True, use_container_width=True)

    st.caption("Objective: maximise modelled production loss avoided within ₹50 Cr. Every feasible combination is evaluated.")

# Footer
st.markdown("---")
st.caption("CHIPSHIELD MVP · Python + Streamlit + NetworkX + Pandas + Plotly · Illustrative scenario model, not an operational forecast.")
