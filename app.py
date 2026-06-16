import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Router Vacuum Hold-Down Tradespace", layout="wide")

st.title("Router Vacuum Hold-Down Pressure Analysis")
st.markdown("""
**Decision Support: Do you need tabs, or will vacuum hold-down keep the part in place?**

All parts are fully cut through (100% depth). This tool calculates whether the remaining 
vacuum hold-down force after cutting is sufficient to resist tool forces and prevent part movement.
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

# Common high-volume parts dropdown
common_parts = {
    "Custom (enter dimensions below)": {"length": 12.0, "width": 8.0, "thickness": 0.75},
    "Peeler": {"length": 12.0, "width": 3.0, "thickness": 1.0},
    "Part A": {"length": 12.0, "width": 8.0, "thickness": 0.75},
    "Part B": {"length": 16.0, "width": 10.0, "thickness": 0.5},
    "Part C": {"length": 24.0, "width": 12.0, "thickness": 1.0},
    "Part D": {"length": 8.0, "width": 6.0, "thickness": 0.5},
    "Part E": {"length": 18.0, "width": 14.0, "thickness": 0.75},
}

selected_part = st.sidebar.selectbox(
    "Select Part Type",
    list(common_parts.keys()),
    help="Choose a common high-volume part or 'Custom' to enter your own dimensions"
)

# Load dimensions from selection
default_dims = common_parts[selected_part]

part_length = st.sidebar.number_input(
    "Part Length (in)", 1.0, 48.0, default_dims["length"], 0.5,
    disabled=(selected_part != "Custom (enter dimensions below)")
)
part_width = st.sidebar.number_input(
    "Part Width (in)", 1.0, 48.0, default_dims["width"], 0.5,
    disabled=(selected_part != "Custom (enter dimensions below)")
)
part_thickness = st.sidebar.number_input(
    "Part Thickness (in)", 0.25, 3.0, default_dims["thickness"], 0.25,
    disabled=(selected_part != "Custom (enter dimensions below)")
)
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
    Compute hold-down force vs cutting force for fully cut-out parts.
    Assumption: part is 100% through-cut, vacuum seal is broken along perimeter.
    """
    results = []

    part_area = part_l * part_w  # in²
    part_perimeter = 2 * (part_l + part_w)  # in
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
    chip_area = chip_load * part_t  # in² (width of cut = thickness)
    cutting_force_lateral = Kc * chip_area  # lb

    # When part is fully cut out, perimeter holes lose vacuum
    # Estimate: holes within one hole-spacing distance of perimeter are compromised
    perimeter_holes_lost = int(part_perimeter / h_spacing)
    
    # Calculate active holes after cut-out
    active_holes = max(0, total_holes - perimeter_holes_lost)
    active_vacuum_area = active_holes * hole_area

    # Hold-down force = vacuum pressure × effective area + part weight
    hold_down_force = vacuum_psi * active_vacuum_area + part_weight

    # Friction coefficient for wood/MDF on spoilboard
    friction_coeff = 0.3
    max_resistive_force = hold_down_force * friction_coeff

    # Movement risk ratio
    movement_risk = cutting_force_lateral / max_resistive_force if max_resistive_force > 0 else 99

    # Safety factor
    safety_factor = hold_down_force / cutting_force_lateral if cutting_force_lateral > 0 else 99

    # Quality score (1.0 = no risk, 0.0 = certain movement)
    quality_score = max(0, min(1.0, 1.0 - movement_risk))

    # Recommendation
    needs_tabs = "YES - TABS REQUIRED" if movement_risk >= 1.0 else "NO - Vacuum Sufficient"

    results.append({
        "Total Holes Under Part": total_holes,
        "Perimeter Holes Lost": perimeter_holes_lost,
        "Active Holes After Cut-Out": active_holes,
        "Total Vacuum Area (in²)": round(total_vacuum_area, 2),
        "Active Vacuum Area (in²)": round(active_vacuum_area, 2),
        "Hold-Down Force (lb)": round(hold_down_force, 2),
        "Max Resistive Force (lb)": round(max_resistive_force, 2),
        "Cutting Force (lb)": round(cutting_force_lateral, 2),
        "Safety Factor": round(safety_factor, 2),
        "Movement Risk Ratio": round(movement_risk, 3),
        "Quality Score": round(quality_score, 3),
        "Tabs Required?": needs_tabs,
    })

    return pd.DataFrame(results), total_holes, part_area, part_weight, total_vacuum_area, active_holes


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
df_cut, total_holes, part_area, part_weight, vacuum_area, active_holes = compute_tradespace(
    holding_force_psi, part_length, part_width, part_thickness, material_density,
    hole_spacing, hole_diameter, tool_diameter, feed_rate, spindle_speed, num_flutes
)

# --- Display Metrics ---
st.subheader("Current Configuration Analysis")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Vacuum Pressure", f"{vacuum_pressure_inHg} inHg")
col2.metric("Part Area", f"{part_area:.1f} in²")
col3.metric("Part Weight", f"{part_weight:.2f} lb")
col4.metric("Total Holes", f"{total_holes}")
col5.metric("Active After Cut", f"{active_holes}")

st.markdown("---")

# Display result prominently
result_row = df_cut.iloc[0]
if result_row["Movement Risk Ratio"] >= 1.0:
    st.error(f"⚠️ **{result_row['Tabs Required?']}** — Hold-down force insufficient after cut-out.")
else:
    st.success(f"✅ **{result_row['Tabs Required?']}** — Part will stay in place.")

col_a, col_b, col_c = st.columns(3)
col_a.metric("Hold-Down Force", f"{result_row['Hold-Down Force (lb)']:.2f} lb")
col_b.metric("Cutting Force", f"{result_row['Cutting Force (lb)']:.2f} lb")
col_c.metric("Safety Factor", f"{result_row['Safety Factor']:.2f}", 
             delta="Safe" if result_row['Safety Factor'] > 1.5 else "At Risk",
             delta_color="normal" if result_row['Safety Factor'] > 1.5 else "inverse")

st.markdown("---")

# --- Tab Layout ---
tab1, tab2 = st.tabs([
    "Current Part Analysis",
    "Part Size Tradespace"
])

with tab1:
    st.subheader("Detailed Breakdown (100% Cut-Out)")
    
    st.dataframe(df_cut.T, use_container_width=True)
    
    st.markdown("### Force Balance")
    st.markdown(f"""
    - **Hold-down force available:** {result_row['Hold-Down Force (lb)']:.2f} lb
    - **Maximum resistive force (with friction):** {result_row['Max Resistive Force (lb)']:.2f} lb
    - **Cutting force to resist:** {result_row['Cutting Force (lb)']:.2f} lb
    - **Movement risk ratio:** {result_row['Movement Risk Ratio']:.3f} (>1.0 means part will move)
    
    **Interpretation:**  
    {'⚠️ Part will likely shift or fly off. Use tabs or increase vacuum pressure.' if result_row['Movement Risk Ratio'] >= 1.0 else '✅ Vacuum hold-down is sufficient. No tabs needed.'}
    """)
    
    st.markdown("### What affects hold-down?")
    st.markdown("""
    **Increases hold-down:**
    - Higher vacuum pressure (more negative inHg)
    - Larger part area (more holes engaged)
    - Closer hole spacing (more holes per area)
    - Larger hole diameter (more suction area)
    
    **Increases cutting force:**
    - Thicker material
    - Higher feed rate
    - Larger tool diameter
    - Lower spindle speed (higher chip load)
    """)

with tab2:
    st.subheader("Part Size Tradespace (Through-Cut Scenario)")
    st.markdown(
        """
        This analysis shows which part sizes are at risk of movement when fully cut through.  
        Use it to identify problematic configurations and plan tab placement for multiple part types.
        """
    )

    df_parts = generate_multi_part_tradespace(
        holding_force_psi, part_width, part_thickness, material_density,
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
    
    st.markdown("""
    **How to read this chart:**
    - **Green points:** Vacuum hold-down is sufficient, no tabs needed
    - **Red points:** Part will move, tabs are required
    - **Size of point:** Larger = higher safety factor (more margin)
    - Hover over points to see detailed force calculations
    """)

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
    
    st.markdown("""
    **Heatmap interpretation:**
    - **Green cells (>1.5):** Safe with good margin
    - **Yellow cells (1.0-1.5):** Marginally safe, consider tabs
    - **Red cells (<1.0):** Tabs required
    - Darker green = higher safety factor = more forgiving
    """)

    at_risk = df_parts[df_parts["Part Moves"] == "YES"]
    if not at_risk.empty:
        st.warning(
            f"⚠️ {len(at_risk)} of {len(df_parts)} part configurations "
            f"are at risk of movement during through-cut."
        )
    else:
        st.success("✅ All part sizes maintain adequate hold-down during through-cut.")
