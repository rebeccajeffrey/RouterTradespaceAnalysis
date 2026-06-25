import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Planar Calibration Check", layout="wide")

st.title("Planar Machine Calibration Analysis 🔧")
st.markdown("""
Verify planar machine calibration by comparing thickness measurements before and after planing.
A properly calibrated machine should remove material uniformly across the board.
""")

# --- Data Input Section ---
st.sidebar.header("Test Configuration")

# Test data input
test_number = st.sidebar.number_input("Test Number", min_value=1, value=1, step=1)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Test 1 Data")
    starting_length_1 = st.number_input("Starting Length (Test 1)", value=0.9, format="%.4f", key="start1")
    cut_to_1 = st.number_input("Target Cut To (Test 1)", value=0.85, format="%.4f", key="cut1")
    
    st.markdown("**Measurements (inches)**")
    before_front_1 = st.number_input("Front - Before", value=0.946, format="%.4f", key="bf1")
    after_front_1 = st.number_input("Front - After", value=0.8405, format="%.4f", key="af1")
    
    before_mid1_1 = st.number_input("Middle 1 - Before", value=0.958, format="%.4f", key="bm1_1")
    after_mid1_1 = st.number_input("Middle 1 - After", value=0.865, format="%.4f", key="am1_1")
    
    before_mid2_1 = st.number_input("Middle 2 - Before", value=0.952, format="%.4f", key="bm2_1")
    after_mid2_1 = st.number_input("Middle 2 - After", value=0.8525, format="%.4f", key="am2_1")
    
    before_aft_1 = st.number_input("Aft - Before", value=0.9575, format="%.4f", key="ba1")
    after_aft_1 = st.number_input("Aft - After", value=0.85, format="%.4f", key="aa1")

with col2:
    st.subheader("Test 2 Data")
    starting_length_2 = st.number_input("Starting Length (Test 2)", value=0.85, format="%.4f", key="start2")
    cut_to_2 = st.number_input("Target Cut To (Test 2)", value=0.82, format="%.4f", key="cut2")
    
    st.markdown("**Measurements (inches)**")
    before_front_2 = st.number_input("Front - Before", value=0.8405, format="%.4f", key="bf2")
    after_front_2 = st.number_input("Front - After", value=0.8175, format="%.4f", key="af2")
    
    before_mid1_2 = st.number_input("Middle 1 - Before", value=0.865, format="%.4f", key="bm1_2")
    after_mid1_2 = st.number_input("Middle 1 - After", value=0.823, format="%.4f", key="am1_2")
    
    before_mid2_2 = st.number_input("Middle 2 - Before", value=0.8525, format="%.4f", key="bm2_2")
    after_mid2_2 = st.number_input("Middle 2 - After", value=0.826, format="%.4f", key="am2_2")
    
    before_aft_2 = st.number_input("Aft - Before", value=0.85, format="%.4f", key="ba2")
    after_aft_2 = st.number_input("Aft - After", value=0.83, format="%.4f", key="aa2")

# --- Build DataFrames ---
test1_data = pd.DataFrame({
    "Position": ["Front", "Middle 1", "Middle 2", "Aft"],
    "Before": [before_front_1, before_mid1_1, before_mid2_1, before_aft_1],
    "After": [after_front_1, after_mid1_1, after_mid2_1, after_aft_1],
})
test1_data["Material Removed"] = test1_data["Before"] - test1_data["After"]
test1_data["Target Removal"] = starting_length_1 - cut_to_1
test1_data["Deviation from Target"] = test1_data["Material Removed"] - test1_data["Target Removal"]

test2_data = pd.DataFrame({
    "Position": ["Front", "Middle 1", "Middle 2", "Aft"],
    "Before": [before_front_2, before_mid1_2, before_mid2_2, before_aft_2],
    "After": [after_front_2, after_mid1_2, after_mid2_2, after_aft_2],
})
test2_data["Material Removed"] = test2_data["Before"] - test2_data["After"]
test2_data["Target Removal"] = starting_length_2 - cut_to_2
test2_data["Deviation from Target"] = test2_data["Material Removed"] - test2_data["Target Removal"]

# --- Summary Statistics ---
st.markdown("---")
st.header("Calibration Summary")

col_s1, col_s2 = st.columns(2)

with col_s1:
    st.subheader("Test 1 Statistics")
    avg_removal_1 = test1_data["Material Removed"].mean()
    std_removal_1 = test1_data["Material Removed"].std()
    max_dev_1 = test1_data["Deviation from Target"].abs().max()
    
    st.metric("Average Material Removed", f"{avg_removal_1:.4f} in")
    st.metric("Target Removal", f"{test1_data['Target Removal'].iloc[0]:.4f} in")
    st.metric("Standard Deviation", f"{std_removal_1:.4f} in")
    st.metric("Max Deviation from Target", f"{max_dev_1:.4f} in")
    
    if max_dev_1 > 0.01:
        st.error("⚠️ Machine may need calibration (deviation > 0.01 in)")
    elif max_dev_1 > 0.005:
        st.warning("⚠️ Marginal calibration (deviation > 0.005 in)")
    else:
        st.success("✅ Machine is well calibrated")

with col_s2:
    st.subheader("Test 2 Statistics")
    avg_removal_2 = test2_data["Material Removed"].mean()
    std_removal_2 = test2_data["Material Removed"].std()
    max_dev_2 = test2_data["Deviation from Target"].abs().max()
    
    st.metric("Average Material Removed", f"{avg_removal_2:.4f} in")
    st.metric("Target Removal", f"{test2_data['Target Removal'].iloc[0]:.4f} in")
    st.metric("Standard Deviation", f"{std_removal_2:.4f} in")
    st.metric("Max Deviation from Target", f"{max_dev_2:.4f} in")
    
    if max_dev_2 > 0.01:
        st.error("⚠️ Machine may need calibration (deviation > 0.01 in)")
    elif max_dev_2 > 0.005:
        st.warning("⚠️ Marginal calibration (deviation > 0.005 in)")
    else:
        st.success("✅ Machine is well calibrated")

# --- Visualizations ---
st.markdown("---")
st.header("Measurement Analysis")

tab1, tab2, tab3, tab4 = st.tabs(["Before/After Comparison", "Material Removed", "Deviation from Target", "Data Tables"])

with tab1:
    st.subheader("Thickness Before and After Planing")
    
    fig1 = go.Figure()
    
    # Test 1
    fig1.add_trace(go.Scatter(
        x=test1_data["Position"], y=test1_data["Before"],
        mode='lines+markers', name='Test 1 - Before',
        line=dict(color='blue', width=2, dash='dot'),
        marker=dict(size=10)
    ))
    fig1.add_trace(go.Scatter(
        x=test1_data["Position"], y=test1_data["After"],
        mode='lines+markers', name='Test 1 - After',
        line=dict(color='blue', width=2),
        marker=dict(size=10)
    ))
    
    # Test 2
    fig1.add_trace(go.Scatter(
        x=test2_data["Position"], y=test2_data["Before"],
        mode='lines+markers', name='Test 2 - Before',
        line=dict(color='red', width=2, dash='dot'),
        marker=dict(size=10)
    ))
    fig1.add_trace(go.Scatter(
        x=test2_data["Position"], y=test2_data["After"],
        mode='lines+markers', name='Test 2 - After',
        line=dict(color='red', width=2),
        marker=dict(size=10)
    ))
    
    # Target lines
    fig1.add_hline(y=cut_to_1, line_dash="dash", line_color="blue",
                   annotation_text=f"Test 1 Target: {cut_to_1} in")
    fig1.add_hline(y=cut_to_2, line_dash="dash", line_color="red",
                   annotation_text=f"Test 2 Target: {cut_to_2} in")
    
    fig1.update_layout(
        xaxis_title="Position Along Board",
        yaxis_title="Thickness (inches)",
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown("""
    **Interpretation:**
    - Dotted lines show thickness before planing
    - Solid lines show thickness after planing
    - Horizontal dashed lines show target thickness
    - Parallel "after" lines indicate uniform material removal (good calibration)
    - Converging/diverging lines suggest calibration issues
    """)

with tab2:
    st.subheader("Material Removed by Position")
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Bar(
        x=test1_data["Position"],
        y=test1_data["Material Removed"],
        name="Test 1",
        marker_color='lightblue'
    ))
    
    fig2.add_trace(go.Bar(
        x=test2_data["Position"],
        y=test2_data["Material Removed"],
        name="Test 2",
        marker_color='lightcoral'
    ))
    
    fig2.add_hline(y=test1_data["Target Removal"].iloc[0], line_dash="dash",
                   line_color="blue", annotation_text=f"Test 1 Target: {test1_data['Target Removal'].iloc[0]:.4f} in")
    fig2.add_hline(y=test2_data["Target Removal"].iloc[0], line_dash="dash",
                   line_color="red", annotation_text=f"Test 2 Target: {test2_data['Target Removal'].iloc[0]:.4f} in")
    
    fig2.update_layout(
        xaxis_title="Position Along Board",
        yaxis_title="Material Removed (inches)",
        barmode='group',
        height=500
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("""
    **Interpretation:**
    - Bars should be roughly equal height across all positions
    - Bars should align with target line (dashed)
    - Uneven bars indicate non-uniform cutting (calibration needed)
    """)

with tab3:
    st.subheader("Deviation from Target Removal")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        x=test1_data["Position"],
        y=test1_data["Deviation from Target"],
        name="Test 1",
        marker_color=['red' if abs(x) > 0.01 else 'yellow' if abs(x) > 0.005 else 'green' 
                      for x in test1_data["Deviation from Target"]]
    ))
    
    fig3.add_trace(go.Bar(
        x=test2_data["Position"],
        y=test2_data["Deviation from Target"],
        name="Test 2",
        marker_color=['red' if abs(x) > 0.01 else 'yellow' if abs(x) > 0.005 else 'green' 
                      for x in test2_data["Deviation from Target"]]
    ))
    
    fig3.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
    fig3.add_hline(y=0.005, line_dash="dash", line_color="orange", annotation_text="±0.005 in tolerance")
    fig3.add_hline(y=-0.005, line_dash="dash", line_color="orange")
    fig3.add_hline(y=0.01, line_dash="dash", line_color="red", annotation_text="±0.01 in tolerance")
    fig3.add_hline(y=-0.01, line_dash="dash", line_color="red")
    
    fig3.update_layout(
        xaxis_title="Position Along Board",
        yaxis_title="Deviation from Target (inches)",
        barmode='group',
        height=500
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    st.markdown("""
    **Interpretation:**
    - Green bars: within ±0.005 in (excellent)
    - Yellow bars: between ±0.005 and ±0.01 in (acceptable)
    - Red bars: beyond ±0.01 in (needs attention)
    - Positive deviation = removed too much material
    - Negative deviation = removed too little material
    """)

with tab4:
    st.subheader("Test 1 Detailed Data")
    st.dataframe(test1_data, use_container_width=True)
    
    st.download_button(
        "Download Test 1 Data (CSV)",
        test1_data.to_csv(index=False),
        "planar_test1.csv",
        "text/csv"
    )
    
    st.subheader("Test 2 Detailed Data")
    st.dataframe(test2_data, use_container_width=True)
    
    st.download_button(
        "Download Test 2 Data (CSV)",
        test2_data.to_csv(index=False),
        "planar_test2.csv",
        "text/csv"
    )

# --- Calibration Recommendations ---
st.markdown("---")
st.header("Calibration Recommendations")

combined_dev = pd.concat([
    test1_data[["Position", "Deviation from Target"]].assign(Test="Test 1"),
    test2_data[["Position", "Deviation from Target"]].assign(Test="Test 2")
])

problem_positions = combined_dev[combined_dev["Deviation from Target"].abs() > 0.01]

if not problem_positions.empty:
    st.error("### ⚠️ Calibration Issues Detected")
    st.dataframe(problem_positions, use_container_width=True)
    st.markdown("""
    **Recommended Actions:**
    1. Check planar bed levelness at problem positions
    2. Verify knife/cutter head alignment
    3. Inspect rollers for wear or debris
    4. Re-run calibration procedure
    5. Consider professional service if issues persist
    """)
else:
    st.success("### ✅ Planar is Well Calibrated")
    st.markdown("All measurements are within acceptable tolerances. No immediate action required.")
