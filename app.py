import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Tab or No Tab?", layout="wide")

st.title("Tab or No Tab? 🔧")
st.markdown("""
**Your go-to tool for deciding if parts need tabs during CNC routing.**

All parts are fully cut through (100% depth). This tool calculates whether vacuum hold-down 
force is sufficient to keep parts in place, or if tabs are required to prevent movement and flyoff.
""")

# --- Constants & Parameters ---
st.sidebar.header("System Parameters")
st.sidebar.markdown("---")

vacuum_pressure_inHg = st.sidebar.slider(
    "Vacuum Pressure (in Hg)", -25.0, -10.0, -22.0, 0.5,
    help="Vacuum pressure (negative value, typical range -12 to -23 inHg)"
)

# Use actual hold-down equation: y = 5.3926x + 8.7524
# y = holding force in pounds per square foot
# x = vacuum pressure in inches of mercury (use absolute value)
holding_force_psf = 5.3926 * abs(vacuum_pressure_inHg) + 8.7524

# Convert to psi (divide by 144 since 1 ft² = 144 in²)
holding_force_psi = holding_force_psf / 144.0

st.sidebar.markdown("---")
st.sidebar.header("Part & Table Configuration")

# Common high-volume parts dropdown
common_parts = {
    "Custom (enter dimensions below)": {"length": 12.0, "width": 8.0, "thickness": 0.75},
    "Peeler": {"length": 12.0, "width": 3.0, "thickness": 1.0},
}

selected_part = st.sidebar.selectbox(
    "Select Part Type",
    list(common_parts.keys()),
    help="Choose a common high-volume part or 'Custom' to enter your own dimensions"
)

# Load dimensions from selection
default_dims = common_parts[selected_part]

# Check if Peeler is selected to lock tool parameters
is_peeler = (selected_part == "Peeler")

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
st.sidebar.markdown("---")
st.sidebar.header("Material Type")

# Material-specific Cut Force constants (empirically validated)
material_types = {
    "Foam (PVC/PMI)": {
        "Kc": 240,
        "density": 0.010,
        "description": "Low-density structural foam (measured: 2.65 lb @ 250 in/min, 0.75\" thick)"
    },
    "Crush Core Panel (Fiberglass Skins)": {
        "Kc": 1197,
        "density": 0.055,
        "description": "Crush core with fiberglass face sheets (measured: 17.6 lb @ 500 in/min, 0.5\" thick)"
    },
    "Honeycomb Core + Carbon Fiber": {
        "Kc": 25000,
        "density": 0.055,
        "description": "Nomex/Aluminum honeycomb with carbon fiber face sheets (estimated)"
    },
    "Honeycomb Core + Kevlar": {
        "Kc": 30000,
        "density": 0.050,
        "description": "Nomex/Aluminum honeycomb with Kevlar face sheets (estimated)"
    },
    "Phenolic Laminate": {
        "Kc": 40000,
        "density": 0.065,
        "description": "Solid phenolic composite (estimated)"
    },
    "Fiberglass Laminate": {
        "Kc": 35000,
        "density": 0.070,
        "description": "Solid fiberglass (GFRP) (estimated)"
    },
    "Custom": {
        "Kc": 18000,
        "density": 0.065,
        "description": "Enter custom values below"
    }
}

selected_material = st.sidebar.selectbox(
    "Select Material Type",
    list(material_types.keys()),
    index=1,  # Default to Crush Core Panel
    help="Material type affects cut force calculation"
)

material_config = material_types[selected_material]
st.sidebar.caption(f"*{material_config['description']}*")

if selected_material == "Custom":
    Kc = st.sidebar.number_input(
        "Specific Cut Force Kc (psi)",
        5000, 200000, material_config["Kc"], 5000,
        help="Material-specific cut force constant"
    )
    # Allow manual density override for custom
    material_density = st.sidebar.number_input(
        "Material Density (lb/in³)",
        0.001, 0.20, material_config["density"], 0.005
    )
else:
    Kc = material_config["Kc"]
    # Auto-set density based on material, but allow override
    material_density = st.sidebar.number_input(
        "Material Density (lb/in³)",
        0.001, 0.20, material_config["density"], 0.005,
        help=f"Default for {selected_material}: {material_config['density']} lb/in³"
    )

hole_spacing_rows = st.sidebar.number_input(
    "Vacuum Row Spacing (in)", 0.5, 6.0, 1.5, 0.25,
    help="Distance between rows of vacuum holes"
)
hole_spacing_in_row = st.sidebar.number_input(
    "Hole Spacing Within Row (in)", 0.25, 6.0, 0.5, 0.25,
    help="Distance between holes within each row"
)
# Use average spacing for calculations (geometric mean of row and within-row spacing)
hole_spacing = (hole_spacing_rows * hole_spacing_in_row) ** 0.5
hole_diameter_mm = st.sidebar.number_input(
    "Vacuum Hole Diameter (mm)", 3.0, 12.0, 6.35, 0.5,
    help="Typical values: 6mm, 6.35mm (1/4\"), 8mm"
)
# Convert mm to inches for calculations
hole_diameter = hole_diameter_mm / 25.4

st.sidebar.markdown("---")
st.sidebar.header("Tool Parameters")

# Set Peeler-specific tool parameters or allow custom
if is_peeler:
    st.sidebar.info("🔒 Tool parameters locked for Peeler part")
    tool_diameter = 0.25
    num_flutes = 1
    spindle_speed = 23500
    feed_rate = 25
    
    st.sidebar.text(f"Tool Diameter: {tool_diameter} in")
    st.sidebar.text(f"Number of Flutes: {num_flutes}")
    st.sidebar.text(f"Spindle Speed: {spindle_speed} RPM")
    st.sidebar.text(f"Feed Rate: {feed_rate} in/min")
else:
    tool_diameter = st.sidebar.number_input("Tool Diameter (in)", 0.125, 1.0, 0.25, 0.0625)
    feed_rate = st.sidebar.number_input("Feed Rate (in/min)", 50, 800, 300, 25)
    spindle_speed = st.sidebar.number_input("Spindle Speed (RPM)", 8000, 30000, 18000, 1000)
    num_flutes = st.sidebar.selectbox("Number of Flutes", [1, 2, 3], index=1)


# --- Helper Functions ---
def compute_tradespace(vacuum_psi, part_l, part_w, part_t, mat_density,
                       h_spacing, h_dia, t_dia, feed, rpm, flutes, Kc):
    """
    Compute hold-down force vs cut force for fully cut-out parts.
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

    # Approximate lateral cut force (tangential)
    # Using simplified specific cut force model
    # Fc = Kc * chip_area, where Kc is material-specific
    chip_area = chip_load * part_t  # in² (width of cut = thickness)
    cut_force_lateral = Kc * chip_area  # lb

    # When part is fully cut out, perimeter loses vacuum seal
    # Vacuum force acts on the remaining sealed part area, not just hole area
    # Estimate the area that loses vacuum: assume a strip around perimeter loses seal
    # Conservative estimate: lose ~0.5" strip around perimeter after cut-out
    perimeter_strip_width = 0.5  # inches
    
    # Calculate remaining sealed area
    sealed_length = max(0, part_l - 2 * perimeter_strip_width)
    sealed_width = max(0, part_w - 2 * perimeter_strip_width)
    sealed_area = sealed_length * sealed_width  # in²
    
    # If part is too small, use reduced sealed area
    if sealed_area < 0.1 * part_area:
        sealed_area = 0.1 * part_area  # minimum 10% sealed
    
    # Hold-down force = vacuum pressure × sealed area + part weight
    # vacuum_psi is already the holding force per square inch from the equation
    hold_down_force = vacuum_psi * sealed_area + part_weight

    # Friction coefficient for wood/MDF on spoilboard
    friction_coeff = 0.3
    max_resistive_force = hold_down_force * friction_coeff

    # Movement risk ratio
    movement_risk = cut_force_lateral / max_resistive_force if max_resistive_force > 0 else 99

    # Safety factor
    safety_factor = hold_down_force / cut_force_lateral if cut_force_lateral > 0 else 99

    # Quality score (1.0 = no risk, 0.0 = certain movement)
    quality_score = max(0, min(1.0, 1.0 - movement_risk))

    # Recommendation
    needs_tabs = "YES - TABS REQUIRED" if movement_risk >= 1.0 else "NO - Vacuum Sufficient"

    results.append({
        "Total Holes Under Part": total_holes,
        "Sealed Area After Cut (in²)": round(sealed_area, 2),
        "Part Area (in²)": round(part_area, 2),
        "Total Vacuum Area (in²)": round(total_vacuum_area, 2),
        "Hold-Down Force (lb)": round(hold_down_force, 2),
        "Max Resistive Force (lb)": round(max_resistive_force, 2),
        "Cut Force (lb)": round(cut_force_lateral, 2),
        "Safety Factor": round(safety_factor, 2),
        "Movement Risk Ratio": round(movement_risk, 3),
        "Quality Score": round(quality_score, 3),
        "Tabs Required?": needs_tabs,
    })

    return pd.DataFrame(results), total_holes, part_area, part_weight, total_vacuum_area, sealed_area


def generate_multi_part_tradespace(vacuum_psi, part_w, part_t, mat_density,
                                   h_spacing, h_dia, t_dia, feed, rpm, flutes, Kc):
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

            # Through-cut scenario: vacuum seal broken around perimeter
            # Calculate remaining sealed area (lose ~0.5" strip around perimeter)
            perimeter_strip_width = 0.5
            sealed_length = max(0, pl - 2 * perimeter_strip_width)
            sealed_width = max(0, pw - 2 * perimeter_strip_width)
            sealed_area = sealed_length * sealed_width
            
            if sealed_area < 0.1 * part_area:
                sealed_area = 0.1 * part_area
            
            hold_down_force = vacuum_psi * sealed_area + part_weight

            # cut force
            chip_load = feed / (rpm * flutes)
            chip_area = chip_load * part_t
            cut_force = Kc * chip_area

            friction_coeff = 0.3
            max_resistive = hold_down_force * friction_coeff
            movement_risk = cut_force / max_resistive if max_resistive > 0 else 99

            quality_score = max(0, min(1.0, 1.0 - movement_risk))
            safety_factor = hold_down_force / cut_force if cut_force > 0 else 99

            results.append({
                "Part Length (in)": pl,
                "Part Width (in)": pw,
                "Part Area (in²)": part_area,
                "Sealed Area (in²)": round(sealed_area, 2),
                "Total Holes": total_holes,
                "Hold-Down Force (lb)": round(hold_down_force, 2),
                "Cut Force (lb)": round(cut_force, 2),
                "Safety Factor": round(safety_factor, 2),
                "Movement Risk Ratio": round(movement_risk, 3),
                "Quality Score": round(quality_score, 3),
                "Part Moves": "YES" if movement_risk >= 1.0 else "NO",
            })

    return pd.DataFrame(results)


# --- Run Analysis ---
df_cut, total_holes, part_area, part_weight, vacuum_area, sealed_area = compute_tradespace(
    holding_force_psi, part_length, part_width, part_thickness, material_density,
    hole_spacing, hole_diameter, tool_diameter, feed_rate, spindle_speed, num_flutes, Kc
)

# --- Display Metrics ---
st.subheader("Current Configuration Analysis")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Vacuum Pressure", f"{vacuum_pressure_inHg} inHg")
col2.metric("Part Area", f"{part_area:.1f} in²")
col3.metric("Sealed Area", f"{sealed_area:.1f} in²")
col4.metric("Part Weight", f"{part_weight:.2f} lb")
col5.metric("Total Holes", f"{total_holes}")

st.markdown("---")

# Display result prominently
result_row = df_cut.iloc[0]
if result_row["Movement Risk Ratio"] >= 1.0:
    st.error(f"⚠️ **{result_row['Tabs Required?']}** — Hold-down force insufficient after cut-out.")
else:
    st.success(f"✅ **{result_row['Tabs Required?']}** — Part will stay in place.")

col_a, col_b, col_c = st.columns(3)
col_a.metric("Hold-Down Force", f"{result_row['Hold-Down Force (lb)']:.2f} lb")
col_b.metric("Cut Force", f"{result_row['Cut Force (lb)']:.2f} lb")
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
    - **Cut force to resist:** {result_row['Cut Force (lb)']:.2f} lb
    - **Movement risk ratio:** {result_row['Movement Risk Ratio']:.3f} (>1.0 means part will move)
    
    **Interpretation:**  
    {'⚠️ Part will likely shift or fly off. Use tabs or increase vacuum pressure.' if result_row['Movement Risk Ratio'] >= 1.0 else '✅ Vacuum hold-down is sufficient. No tabs needed.'}
    """)
    
    # Add equations
    st.markdown("### 📐 Governing Equations")
    st.latex(r"\text{Hold-Down Force} = \left(\frac{5.3926 \times |P_{vac}| + 8.7524}{144}\right) \times A_{sealed} + W_{part}")
    st.markdown(f"""
    Where:
    - $P_{{vac}}$ = Vacuum pressure ({vacuum_pressure_inHg} inHg)
    - $A_{{sealed}}$ = Sealed part area after cut-out ({sealed_area:.2f} in²)
    - $W_{{part}}$ = Part weight ({part_weight:.2f} lb)
    """)
    
    st.latex(r"\text{Cut Force} = K_c \times \text{chip load} \times t_{part}")
    st.latex(r"\text{where: chip load} = \frac{f}{n \times RPM}")
    st.markdown(f"""
    Where:
    - $K_c$ = Specific cut force ({Kc:,} psi for {selected_material})
    - $f$ = Feed rate ({feed_rate} in/min)
    - $n$ = Number of flutes ({num_flutes})
    - $RPM$ = Spindle speed ({spindle_speed})
    - $t_{{part}}$ = Part thickness ({part_thickness} in)
    """)
    
    # Add calculation details
    with st.expander("📊 See Detailed Calculation Breakdown"):
        st.markdown(f"""
        **Chip Load Calculation:**
        - Feed rate: {feed_rate} in/min
        - Spindle speed: {spindle_speed} RPM
        - Number of flutes: {num_flutes}
        - **Chip load = {feed_rate} ÷ ({spindle_speed} × {num_flutes}) = {feed_rate/(spindle_speed*num_flutes):.6f} in/tooth**
        
        **Cut Force Calculation:**
        - Specific cut force (Kc): {Kc:,} psi (material: {selected_material})
        - Part thickness: {part_thickness} in
        - Chip area = chip load × thickness = {feed_rate/(spindle_speed*num_flutes):.6f} × {part_thickness} = {(feed_rate/(spindle_speed*num_flutes))*part_thickness:.6f} in²
        - **Cut force = Kc × chip area = {Kc:,} × {(feed_rate/(spindle_speed*num_flutes))*part_thickness:.6f} = {result_row['Cut Force (lb)']:.2f} lb**
        
        *Note: If this seems too high or low, adjust Kc value in the Material Type section or select "Custom" to enter your own.*
        """)
    
    st.markdown("### What affects hold-down?")
    st.markdown("""
    **Increases hold-down:**
    - Higher vacuum pressure (more negative inHg)
    - Larger part area (more holes engaged)
    - Closer hole spacing (more holes per area)
    - Larger hole diameter (more suction area)
    
    **Increases cut force:**
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
        
        **What are "configurations"?** Each configuration is a unique combination of part length and width. 
        The app tests a grid of sizes (e.g., 2"×2", 2"×4", 4"×2", 4"×4", etc.) to see which combinations 
        will stay in place vs. which need tabs. Your current tool and material settings are applied to all sizes.
        
        Use this to identify problematic sizes and plan tab placement for multiple part types.
        """
    )

    df_parts = generate_multi_part_tradespace(
        holding_force_psi, part_width, part_thickness, material_density,
        hole_spacing, hole_diameter, tool_diameter, feed_rate, spindle_speed, num_flutes, Kc
    )

    # Cap safety factor for better visualization
    df_parts["Safety Factor Capped"] = df_parts["Safety Factor"].clip(upper=10)
    
    fig4 = px.scatter(
        df_parts,
        x="Part Length (in)",
        y="Part Width (in)",
        color="Quality Score",
        size="Safety Factor Capped",
        hover_data=["Hold-Down Force (lb)", "Cut Force (lb)",
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
            f"⚠️ **{len(at_risk)} of {len(df_parts)} part size combinations require tabs**\n\n"
            f"The tradespace tested {len(df_parts)} different part sizes (varying length and width). "
            f"For {len(at_risk)} of these combinations, the cut force exceeds the available "
            f"vacuum hold-down force after the part is fully cut out, meaning the part will shift or fly off without tabs.\n\n"
            f"**What this means:** These size/shape combinations need tabs to stay in place during cutting. "
            f"The scatter plot and heatmap above show which specific sizes are at risk (red/yellow areas)."
        )
    else:
        st.success(
            f"✅ **All {len(df_parts)} part size combinations are safe without tabs**\n\n"
            f"The vacuum hold-down force is sufficient for all tested part sizes with your current settings."
        )
