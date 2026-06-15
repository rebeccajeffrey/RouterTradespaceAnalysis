import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Router Vacuum Hold-Down Tradespace", layout="wide")

st.title("Router Vacuum Hold-Down Pressure Analysis")
st.markdown("""
Analyze the tradespace of CNC router vacuum hold-down configurations to determine
if through-cutting causes part movement due to pressure loss and tool forces.
The goal is to maintain part quality by ensuring adequate hold-down force throughout the cut.
""")

# --- Constants & Parameters ---
st.sidebar.header("System Parameters")
st.sidebar.markdown("---")

vacuum_pressure_inHg = st.sidebar.slider(
    "Vacuum Pressure (in Hg)", -25.0, -10.0, -15.0, 0.5,
    help="Vacuum pressure (negative value, typical range -12 to -23 inHg)"
)

# Use actual hold-down equation: y = 5.3926x + 8.7524
# y = holding force in pounds per square foot
# x = vacuum pressure in inches of mercury
holding_force_psf = 5.3926 * vacuum_pressure_inHg + 8.7524

# Convert to psi (divide by 144 since 1 ft² = 144 in²)
holding_force_psi = holding_force_psf / 144.0

st.sidebar.markdown("---")
st.sidebar.header("Part & Table Configuration")

part_length = st.sidebar.number_input("Part Length (in)", 1.0, 48.0, 12.0, 0.5)
part_width = st.sidebar.number_input("Part Width (in)", 1.0, 48.0, 8.0, 0.5)
part_thickness = st.sidebar.number_input("Part Thickness (in)", 0.25, 3.0, 0.75, 0.25)
material_density = st.sidebar.number_input(
    "Material Density (lb/in³)", 0.01, 0.10, 0.025, 0.005,
    help="MDF ≈ 0.028, Plywood ≈ 0.022, Hardwood ≈ 0.025"
)

hole_spacing = st.sidebar.number_input(
    "Vacuum Hole Spacing (in)", 0.5, 6.0, 2.0, 0.25,
    help="Distance between vacuum holes on the table grid"
)
hole_diameter = st.sidebar.number_input(
    "Vacuum Hole Diameter (in)", 0.125, 0.5, 0.25, 0.0625
)

st.sidebar.markdown("---")
st.sidebar.header("Tool Parameters")

tool_diameter = st.sidebar.number_input("Tool Diameter (in)", 0.125, 1.0, 0.25, 0.0625)
feed_rate = st.sidebar.number_input("Feed Rate (in/min)", 50, 800, 300, 25)
spindle_speed = st.sidebar.number_input("Spindle Speed (RPM)", 8000, 30000, 18000, 1000)
num_flutes = st.sidebar.selectbox("Number of Flutes", [1, 2, 3], index=1)


# --- Physics Calculations ---
def compute_tradespace(vacuum_psi, part_l, part_w, part_t, mat_density,
                       h_spacing, h_dia, t_dia, feed, rpm, flutes):
    """
    Compute hold-down force vs cutting force across a range of through-cut scenarios.
    """
    results = []

    part_area = part_l * part_w  # in²
    part_weight = part_area * part_t * mat_density  # lb

    # Number of vacuum holes under the part
    holes_x = max(1, int(part_l / h_spacing))
    holes_y = max(1, int(part_w / h_spacing))
    total_holes = holes_x * holes_y
    hole_area = np.pi * (h_dia / 2) ** 2  # area per hole in²

    # Total effective vacuum area (holes exposed to vacuum)
    total_vacuum_area = total_holes * hole_area  # in²

    # Chip load calculation
    chip_load = feed / (rpm * flutes)  # in/tooth

    # Approximate lateral cutting force (tangential)
    # Using simplified specific cutting force model
    # Fc = Kc * chip_area, Kc for wood ~15,000-25,000 PSI
    Kc = 18000  # specific cutting force for wood/composite (PSI)
    chip_area = chip_load * part_t  # in² (width of cut = thickness in through-cut)
    cutting_force_lateral = Kc * chip_area  # lb

    # Vary the percentage of through-cut (how much material is left as onion skin)
    cut_through_percentages = np.arange(0, 105, 5)  # 0% to 100%

    for pct in cut_through_percentages:
        depth_of_cut = part_t * (pct / 100.0)

        # When cutting through, some vacuum holes along the cut path lose pressure
        # Estimate holes compromised by the cut (along one edge)
        cut_length = part_l  # assume cut runs full length
        holes_along_cut = max(0, int(cut_length / h_spacing))

        # Fraction of holes lost when fully through
        if pct >= 100:
            holes_lost = holes_along_cut
        else:
            holes_lost = 0  # onion skin maintains seal

        active_holes = total_holes - holes_lost
        active_vacuum_area = active_holes * hole_area

        # Hold-down force = vacuum pressure × effective area + part weight
        hold_down_force = vacuum_psi * active_vacuum_area + part_weight

        # Effective cutting force at this depth
        if pct > 0:
            effective_cut_force = cutting_force_lateral * (pct / 100.0)
        else:
            effective_cut_force = 0

        # Safety factor
        if effective_cut_force > 0:
            safety_factor = hold_down_force / effective_cut_force
        else:
            safety_factor = 99.0  # no cutting force = safe

        # Risk of movement (friction coefficient ~0.3 for wood on spoilboard)
        friction_coeff = 0.3
        max_resistive_force = hold_down_force * friction_coeff
        movement_risk = effective_cut_force / max_resistive_force if max_resistive_force > 0 else 0

        # Quality score (1.0 = no risk, 0.0 = certain movement)
        quality_score = max(0, min(1.0, 1.0 - movement_risk))

        results.append({
            "Cut-Through (%)": pct,
            "Depth of Cut (in)": round(depth_of_cut, 4),
            "Active Holes": active_holes,
            "Hold-Down Force (lb)": round(hold_down_force, 2),
            "Cutting Force (lb)": round(effective_cut_force, 2),
            "Safety Factor": round(safety_factor, 2),
            "Movement Risk Ratio": round(movement_risk, 3),
            "Quality Score": round(quality_score, 3),
        })

    return pd.DataFrame(results), total_holes, part_area, part_weight, total_vacuum_area


def generate_multi_part_tradespace(vacuum_psi, part_w, part_t, mat_density,
                                   h_spacing, h_dia, t_dia, feed, rpm, flutes):
    """
    Generate tradespace across varying part sizes and cut configurations.
    """
    results = []
    part_lengths = np.arange(2, 26, 2)
    part_widths = np.arange(2, 14, 2)

    for pl in part_lengths:
        for pw in part_widths:
            part_area = pl * pw
            part_weight = part_area * part_t * mat_density

            holes_x = max(1, int(pl / h_spacing))
            holes_y = max(1, int(pw / h_spacing))
            total_holes = holes_x * holes_y
            hole_area = np.pi * (h_dia / 2) ** 2

            # Through-cut scenario: lose holes along longest edge
            holes_along_cut = max(0, int(pl / h_spacing))
            active_holes = total_holes - holes_along_cut
            active_vacuum_area = active_holes * hole_area

            hold_down_force = vacuum_psi * active_vacuum_area + part_weight

            # Cutting force
            chip_load = feed / (rpm * flutes)
            chip_area = chip_load * part_t
            Kc = 18000
            cutting_force = Kc * chip_area

            friction_coeff = 0.3
            max_resistive = hold_down_force * friction_coeff
            movement_risk = cutting_force / max_resistive if max_resistive > 0 else 99

            quality_score = max(0, min(1.0, 1.0 - movement_risk))
            safety_factor = hold_down_force / cutting_force if cutting_force > 0 else 99

            results.append({
                "Part Length (in)": pl,
                "Part Width (in)": pw,
                "Part Area (in²)": part_area,
                "Total Holes": total_holes,
                "Active Holes (through-cut)": active_holes,
                "Hold-Down Force (lb)": round(hold_down_force, 2),
                "Cutting Force (lb)": round(cutting_force, 2),
                "Safety Factor": round(safety_factor, 2),
                "Movement Risk Ratio": round(movement_risk, 3),
                "Quality Score": round(quality_score, 3),
                "Part Moves": "YES" if movement_risk >= 1.0 else "NO",
            })

    return pd.DataFrame(results)


# --- Run Analysis ---
df_cut, total_holes, part_area, part_weight, vacuum_area = compute_tradespace(
    vacuum_pressure_psi, part_length, part_width, part_thickness, material_density,
    hole_spacing, hole_diameter, tool_diameter, feed_rate, spindle_speed, num_flutes
)

# --- Display Metrics ---
st.subheader("System Overview")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Vacuum Pressure", f"{vacuum_pressure_inHg} inHg")
col2.metric("Part Area", f"{part_area:.1f} in²")
col3.metric("Part Weight", f"{part_weight:.2f} lb")
col4.metric("Vacuum Holes Under Part", f"{total_holes}")
col5.metric("Total Vacuum Area", f"{vacuum_area:.2f} in²")

st.markdown("---")

# --- Tab Layout ---
tab1, tab2, tab3 = st.tabs([
    "Cut-Through Analysis",
    "Part Size Tradespace",
    "Data Tables"
])

with tab1:
    st.subheader("Hold-Down Force vs Cutting Force During Through-Cut")

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df_cut["Cut-Through (%)"],
        y=df_cut["Hold-Down Force (lb)"],
        name="Hold-Down Force (lb)",
        mode="lines+markers",
        line=dict(color="blue", width=2),
    ))
    fig1.add_trace(go.Scatter(
        x=df_cut["Cut-Through (%)"],
        y=df_cut["Cutting Force (lb)"],
        name="Cutting Force (lb)",
        mode="lines+markers",
        line=dict(color="red", width=2),
    ))
    fig1.update_layout(
        xaxis_title="Cut-Through Percentage (%)",
        yaxis_title="Force (lb)",
        height=450,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Quality & Safety Plot
    col_a, col_b = st.columns(2)

    with col_a:
        fig2 = px.line(
            df_cut, x="Cut-Through (%)", y="Safety Factor",
            title="Safety Factor vs Cut Depth",
            markers=True,
        )
        fig2.add_hline(y=1.0, line_dash="dash", line_color="red",
                       annotation_text="Movement Threshold")
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        fig3 = px.line(
            df_cut, x="Cut-Through (%)", y="Quality Score",
            title="Part Quality Score vs Cut Depth",
            markers=True,
            color_discrete_sequence=["green"],
        )
        fig3.add_hline(y=0.0, line_dash="dash", line_color="red",
                       annotation_text="Part Will Move")
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

    # Key finding
    critical_row = df_cut[df_cut["Movement Risk Ratio"] >= 1.0]
    if not critical_row.empty:
        critical_pct = critical_row.iloc[0]["Cut-Through (%)"]
        st.error(
            f"⚠️ Part movement predicted at **{critical_pct}% cut-through**. "
            f"Consider onion-skin cuts, tabs, or increasing vacuum pressure."
        )
    else:
        st.success(
            "✅ Hold-down force is sufficient across all cut depths for this configuration."
        )

with tab2:
    st.subheader("Part Size Tradespace (Through-Cut Scenario)")
    st.markdown(
        "This shows which part sizes are at risk of movement when fully cut through."
    )

    df_parts = generate_multi_part_tradespace(
        vacuum_pressure_psi, part_width, part_thickness, material_density,
        hole_spacing, hole_diameter, tool_diameter, feed_rate, spindle_speed, num_flutes
    )

    fig4 = px.scatter(
        df_parts,
        x="Part Length (in)",
        y="Part Width (in)",
        color="Quality Score",
        size="Safety Factor",
        hover_data=["Hold-Down Force (lb)", "Cutting Force (lb)",
                    "Safety Factor", "Part Moves"],
        color_continuous_scale="RdYlGn",
        title="Part Size vs Quality Score (Green = Safe, Red = Will Move)",
    )
    fig4.update_layout(height=500)
    st.plotly_chart(fig4, use_container_width=True)

    # Heatmap
    pivot = df_parts.pivot_table(
        index="Part Width (in)", columns="Part Length (in)",
        values="Safety Factor", aggfunc="mean"
    )
    fig5 = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn",
        title="Safety Factor Heatmap by Part Dimensions",
        labels=dict(x="Part Length (in)", y="Part Width (in)", color="Safety Factor"),
        aspect="auto",
    )
    fig5.update_layout(height=400)
    st.plotly_chart(fig5, use_container_width=True)

    at_risk = df_parts[df_parts["Part Moves"] == "YES"]
    if not at_risk.empty:
        st.warning(
            f"⚠️ {len(at_risk)} of {len(df_parts)} part configurations "
            f"are at risk of movement during through-cut."
        )
    else:
        st.success("✅ All part sizes maintain adequate hold-down during through-cut.")

with tab3:
    st.subheader("Cut-Through Analysis Data")
    st.dataframe(df_cut, use_container_width=True)

    st.subheader("Part Size Tradespace Data")
    st.dataframe(df_parts, use_container_width=True)

    st.download_button(
        "Download Cut-Through Data (CSV)",
        df_cut.to_csv(index=False),
        "cut_through_analysis.csv",
        "text/csv",
    )
    st.download_button(
        "Download Part Size Data (CSV)",
        df_parts.to_csv(index=False),
        "part_size_tradespace.csv",
        "text/csv",
    )
