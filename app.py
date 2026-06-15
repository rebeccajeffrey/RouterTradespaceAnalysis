import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Tradespace Analysis", layout="wide")

st.title("Tradespace Analysis Tool")
st.markdown("""
Explore design alternatives across competing objectives. Upload your data or use
the built-in example to visualize the tradespace and identify Pareto-optimal solutions.
""")


# --- Helper Functions ---
def compute_pareto_front(df, obj1, obj2, maximize_obj1, maximize_obj2):
    """Identify Pareto-optimal points given two objectives."""
    points = df[[obj1, obj2]].values.copy()

    # Flip signs so we always minimize internally
    if maximize_obj1:
        points[:, 0] = -points[:, 0]
    if maximize_obj2:
        points[:, 1] = -points[:, 1]

    is_pareto = np.ones(len(points), dtype=bool)
    for i in range(len(points)):
        if not is_pareto[i]:
            continue
        for j in range(len(points)):
            if i == j or not is_pareto[j]:
                continue
            # j dominates i if j <= i in all objectives and j < i in at least one
            if (points[j] <= points[i]).all() and (points[j] < points[i]).any():
                is_pareto[i] = False
                break

    return is_pareto


def generate_example_data(n=50):
    """Generate synthetic tradespace data for demonstration."""
    np.random.seed(42)
    names = [f"Design {i+1}" for i in range(n)]
    cost = np.random.uniform(10, 100, n)
    performance = 80 - 0.5 * cost + np.random.normal(0, 10, n)
    weight = np.random.uniform(5, 50, n)
    reliability = np.clip(0.7 + 0.002 * cost + np.random.normal(0, 0.05, n), 0.5, 0.99)

    return pd.DataFrame({
        "Design": names,
        "Cost ($M)": np.round(cost, 2),
        "Performance": np.round(performance, 2),
        "Weight (kg)": np.round(weight, 2),
        "Reliability": np.round(reliability, 3),
    })


# --- Data Input ---
st.sidebar.header("Data Source")
data_source = st.sidebar.radio("Choose data source:", ["Example Data", "Upload CSV"])

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your tradespace CSV", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        st.info("Please upload a CSV file with your design alternatives and attributes.")
        st.stop()
else:
    df = generate_example_data()

st.sidebar.markdown("---")
st.sidebar.header("Axis Configuration")

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

if len(numeric_cols) < 2:
    st.error("Need at least 2 numeric columns for tradespace analysis.")
    st.stop()

x_axis = st.sidebar.selectbox("X-Axis (Objective 1)", numeric_cols, index=0)
y_axis = st.sidebar.selectbox("Y-Axis (Objective 2)", numeric_cols, index=1)

maximize_x = st.sidebar.checkbox(f"Maximize {x_axis}", value=False)
maximize_y = st.sidebar.checkbox(f"Maximize {y_axis}", value=True)

# Optional color/size dimensions
color_col = st.sidebar.selectbox("Color by", ["None"] + numeric_cols, index=0)
size_col = st.sidebar.selectbox("Size by", ["None"] + numeric_cols, index=0)

# --- Pareto Front ---
pareto_mask = compute_pareto_front(df, x_axis, y_axis, maximize_x, maximize_y)
df["Pareto Optimal"] = pareto_mask

# --- Visualization ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Tradespace Plot")

    fig = px.scatter(
        df,
        x=x_axis,
        y=y_axis,
        color=color_col if color_col != "None" else None,
        size=size_col if size_col != "None" else None,
        hover_data=df.columns.tolist(),
        color_continuous_scale="Viridis",
    )

    # Highlight Pareto front
    pareto_df = df[df["Pareto Optimal"]].sort_values(x_axis)
    fig.add_trace(
        go.Scatter(
            x=pareto_df[x_axis],
            y=pareto_df[y_axis],
            mode="lines+markers",
            name="Pareto Front",
            line=dict(color="red", width=2, dash="dash"),
            marker=dict(size=10, symbol="star", color="red"),
        )
    )

    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Summary Statistics")
    st.metric("Total Designs", len(df))
    st.metric("Pareto-Optimal Designs", int(pareto_mask.sum()))
    st.metric(f"{x_axis} Range", f"{df[x_axis].min():.2f} – {df[x_axis].max():.2f}")
    st.metric(f"{y_axis} Range", f"{df[y_axis].min():.2f} – {df[y_axis].max():.2f}")

# --- Data Table ---
st.subheader("Design Alternatives")
show_pareto_only = st.checkbox("Show Pareto-optimal designs only")

if show_pareto_only:
    st.dataframe(df[df["Pareto Optimal"]], use_container_width=True)
else:
    st.dataframe(df, use_container_width=True)

# --- Parallel Coordinates ---
st.subheader("Parallel Coordinates")
selected_dims = st.multiselect(
    "Select dimensions to display",
    numeric_cols,
    default=numeric_cols[:4] if len(numeric_cols) >= 4 else numeric_cols,
)

if selected_dims:
    fig_parallel = px.parallel_coordinates(
        df,
        dimensions=selected_dims,
        color=selected_dims[0],
        color_continuous_scale="Turbo",
    )
    fig_parallel.update_layout(height=400)
    st.plotly_chart(fig_parallel, use_container_width=True)
