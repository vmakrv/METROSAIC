import streamlit as st
import pandas as pd
import numpy as np
from optimizer import optimize_transit


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="METROSAIC",
    layout="wide"
)



# ---------------------------------------------------------
# CUSTOM STYLING
# ---------------------------------------------------------

st.markdown(
    """
    <style>

        /* Main application background */
        .stApp {
            background-color: #000000;
        }

        /* Make the top header transparent */
        [data-testid="stHeader"] {
            background-color: transparent;
        }

        /* Main content text */
        .stApp p,
        .stApp label,
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4 {
            color: #FFFFFF;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #262730;
        }

        /* Sidebar text */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {
            color: #FFFFFF;
        }

        /* Warning boxes */
        div[data-testid="stAlert"] {
          background-color: #00b5d9 !important;
          color: white !important;
          border-radius: 8px !important;
          overflow: hidden !important;
        }

        /* Warning text */
        div[data-testid="stAlert"] p {
          color: white !important;
        }


    </style>
    """,
    unsafe_allow_html=True
)



# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

st.markdown(
    """
    <h1 style="
        font-family: 'Bahnschrift', 'Arial', sans-serif;
        font-size: 60px;
        font-weight: 800;
        letter-spacing: 1px;
        margin-bottom: 20px;
    ">
        METROSAIC: Transit Schedule Optimizer
    </h1>
    """,
    unsafe_allow_html=True
)

st.write(
    """
    Optimize bus assignments across a hub-and-spoke transit network using observed demand and route loop times.
    In this algorithm, demand represents the number of riders on each route during each time block and loop time represents the time required for a bus to complete a route (depart from and return to the origin). \n
    *NOTE: The optimization algroithm treats your demand matrix as observed demand that must be fully covered. It does not forecast demand.*
    """
)


# ---------------------------------------------------------
# SIDEBAR — MODEL PARAMETERS
# ---------------------------------------------------------

st.sidebar.header("MODEL PARAMETERS")

B = st.sidebar.number_input(
    "Number of Buses",
    min_value=1,
    max_value=500,
    value=40,
    step=1
)

tau = st.sidebar.number_input(
    "Time Period Length (minutes)",
    min_value=0.1,
    value=120.0,
    step=5.0,
    help="used to calculate effective capacity"
)

capacity = st.sidebar.number_input(
    "Bus Capacity",
    min_value=0.1,
    value=35.0,
    step=1.0
)

cost_A = st.sidebar.number_input(
    "Bus Activation Cost",
    min_value=0.0,
    value=150.0,
    step=10.0
)

st.sidebar.write("")
st.sidebar.write("")
st.sidebar.write("")


st.sidebar.subheader("OBJECTIVE WEIGHTS")

priority = st.sidebar.slider(
    "Demand Allocation Priority",
    min_value=0,
    max_value=100,
    value=50,
    step=5,
    help=(
        "controls the tradeoff between minimizing bus activation cost and prioritizing bus allocation toward higher-demand routes"
    )
)

beta = priority / 100
alpha = 1 - beta

st.sidebar.caption(
    f"Alpha (fleet efficiency): {alpha:.0%}<br>"
    f"Beta (service frequency): {beta:.0%}",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    "<div style='margin-top: 8px;'></div>",
    unsafe_allow_html=True
)

delta = st.sidebar.number_input(
    "Delta",
    min_value=0.0001,
    value=0.1,
    step=0.01,
    format="%.4f",
    help=(
        "small positive value used in the reciprocal demand allocation penalty"
    )
)



# ---------------------------------------------------------
# DATA INPUT METHOD
# ---------------------------------------------------------

st.markdown(
    "<h2 style='margin-top: 80px; font-weight: 700;'>PROVIDE YOUR DATA</h2>",
    unsafe_allow_html=True
)

input_method = st.radio(
    "How would you like to provide your data?",
    [
        "Upload CSV Files",
        "Input Directly"
    ],
    horizontal=True
)


# ---------------------------------------------------------
# CSV INPUT
# ---------------------------------------------------------

if input_method == "Upload CSV Files":

    st.subheader("Upload Demand Data")

    demand_file = st.file_uploader(
        "Demand CSV",
        type=["csv"],
        key="demand_upload"
    )

    st.caption(
        """
        Dataset should be formatted as Route × Time Block (rows = routes, columns = time blocks). 
        Values should be # of riders.
        """
    )

    st.subheader("Upload Loop Time Data")

    loop_file = st.file_uploader(
        "Loop Time CSV",
        type=["csv"],
        key="loop_upload"
    )

    st.caption(
        """
        Dataset should be formatted as Route × Time Block (rows = routes, columns = time blocks).
        Values should be in minutes.
        """
    )

    if demand_file is not None and loop_file is not None:

        try:

            demand_df = pd.read_csv(demand_file)
            loop_df = pd.read_csv(loop_file)

            demand = demand_df.values.astype(float)
            loop_time = loop_df.values.astype(float)

            st.write("Demand Matrix:")
            st.dataframe(demand_df, use_container_width=True)

            st.write("Loop Time Matrix:")
            st.dataframe(loop_df, use_container_width=True)

        except Exception as e:

            st.error(
                f"Could not read the uploaded files: {e}"
            )

            demand = None
            loop_time = None

    else:

        demand = None
        loop_time = None


# ---------------------------------------------------------
# MANUAL MATRIX INPUT
# ---------------------------------------------------------

else:

    st.subheader("Create Your Network")

    col1, col2 = st.columns(2)

    with col1:

        R = st.number_input(
            "Number of Routes",
            min_value=1,
            max_value=100,
            value=3,
            step=1
        )

    with col2:

        T = st.number_input(
            "Number of Time Blocks",
            min_value=1,
            max_value=100,
            value=4,
            step=1
        )

    st.markdown("### Demand Matrix")

    st.caption(
        "Rows = Routes. Columns = Time Blocks. Values are # of riders."
    )

    demand_default = pd.DataFrame(
        np.zeros((R, T)),
        index=[
            f"Route {r + 1}"
            for r in range(R)
        ],
        columns=[
            f"Time Block {t + 1}"
            for t in range(T)
        ]
    )

    demand_df = st.data_editor(
        demand_default,
        key=f"demand_editor_{R}_{T}",
        use_container_width=True,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                min_value=0,
                step=1
            )
            for column in demand_default.columns
        }
    )

    st.markdown("### Loop Time Matrix")

    st.caption(
        "Rows = Routes. Columns = Time Blocks. Values are minutes."
    )

    loop_default = pd.DataFrame(
        np.full((R, T), 60.0),
        index=[
            f"Route {r + 1}"
            for r in range(R)
        ],
        columns=[
            f"Time Block {t + 1}"
            for t in range(T)
        ]
    )

    loop_df = st.data_editor(
        loop_default,
        key=f"loop_editor_{R}_{T}",
        use_container_width=True,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                min_value=0.1,
                step=1.0
            )
            for column in loop_default.columns
        }
    )

    demand = demand_df.values.astype(float)
    loop_time = loop_df.values.astype(float)


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

if demand is not None and loop_time is not None:

    if demand.shape != loop_time.shape:

        st.error(
            f"""
            The demand and loop time datasets must have the same dimensions.

            Demand: {demand.shape}

            Loop Time: {loop_time.shape}
            """
        )

        valid_data = False

    elif np.any(demand < 0):

        st.error("The demand dataset cannot contain negative values.")

        valid_data = False

    elif np.any(loop_time <= 0):

        st.error("The loop time dataset must be greater than zero.")

        valid_data = False

    else:

        valid_data = True

else:

    valid_data = False


# ---------------------------------------------------------
# RUN OPTIMIZATION
# ---------------------------------------------------------

st.markdown(
    "<h2 style='margin-top: 80px; font-weight: 700;'>RUN OPTIMIZATION ALGORITHM</h2>",
    unsafe_allow_html=True
)

if valid_data:

    st.write(
        f"""
        **Network:** {demand.shape[0]} routes ×
        {demand.shape[1]} time blocks

        **Available Buses:** {B}
        """
    )

    run_button = st.button(
        "Generate Optimal Schedule",
        type="primary",
        use_container_width=True
    )

    if run_button:

        with st.spinner(
            "Optimizing bus assignments..."
        ):

            try:

                results = optimize_transit(
                    demand=demand,
                    loop_time=loop_time,
                    B=int(B),
                    tau=float(tau),
                    capacity=float(capacity),
                    cost_A=float(cost_A),
                    alpha=float(alpha),
                    beta=float(beta),
                    delta=float(delta)
                )

                st.session_state["results"] = results

                st.success(
                    "Optimization Completed"
                )

            except Exception as e:

                st.error(
                    f"Optimization Failed: {e}"
                )

else:

    st.warning(
        "Provide valid demand and loop time data before running the optimization."
    )


# ---------------------------------------------------------
# RESULTS
# ---------------------------------------------------------

if "results" in st.session_state:

    results = st.session_state["results"]

    st.markdown(
    "<h2 style='margin-top: 80px; font-weight: 700;'>RESULTS</h2>",
    unsafe_allow_html=True)

    # -----------------------------------------------------
    # SUMMARY METRICS
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Objective Value",
            f"{results['objective_value']:,.2f}"
        )

    with col2:
        st.metric(
            "Buses Activated",
            results["num_activated_buses"]
        )

    with col3:
        st.metric(
            "Available Buses",
            int(B)
        )

    with col4:

        fleet_utilization = (
            results["utilization"]["Activated? (0 = No, 1 = Yes)"].sum()
            / int(B)
        )

        st.metric(
            "Fleet Activation",
            f"{fleet_utilization:.1%}"
        )

    st.markdown("---")

    st.write(
        "**Solver Status:**",
        results["solver_status"]
    )

    st.write(
        "**Termination Condition:**",
        results["termination_condition"]
    )

    # -----------------------------------------------------
    # BUS UTILIZATION
    # -----------------------------------------------------

    st.subheader("Fleet Utilization")

    st.dataframe(
        results["utilization"],
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # ROUTE ASSIGNMENTS
    # -----------------------------------------------------

    st.subheader("Route Assignments")

    st.dataframe(
        results["route_summary"],
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # BUS SCHEDULE
    # -----------------------------------------------------

    st.subheader("Bus Schedule")

    if not results["assignments"].empty:

        schedule = results["assignments"].pivot_table(
            index="Bus",
            columns="Time",
            values="Route",
            aggfunc="first",
            fill_value="Off"
        )

        schedule.columns = [
            f"Route Assignment in Time Block {int(c)}"
            for c in schedule.columns
        ]
        
        schedule.columns.name = None
        schedule.index.name = "Bus Number"

        schedule = schedule.reset_index()

        st.dataframe(
            schedule,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.warning(
            "No bus assignments were generated."
        )

    # -----------------------------------------------------
    # DOWNLOADS
    # -----------------------------------------------------

    st.subheader("Download Results")

    col1, col2, col3 = st.columns(3)

    with col1:

        assignments_csv = (
            results["assignments"]
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "Download Assignments CSV",
            assignments_csv,
            "bus_assignments.csv",
            "text/csv",
            use_container_width=True
        )

    with col2:

        route_csv = (
            results["route_summary"]
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "Download Route Results CSV",
            route_csv,
            "route_results.csv",
            "text/csv",
            use_container_width=True
        )

    with col3:

        utilization_csv = (
            results["utilization"]
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "Download Utilization CSV",
            utilization_csv,
            "fleet_utilization.csv",
            "text/csv",
            use_container_width=True
        )
