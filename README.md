# METROSAIC: Transit Schedule Optimizer

**METROSAIC** is an interactive transit scheduling optimization tool designed to help allocate buses across a hub-and-spoke transit network based on observed passenger demand and route loop times.

The application uses a mixed-integer linear programming algorithm to determine how many buses should be activated and how those buses should be assigned to routes across different time blocks.

> **Important:** METROSAIC optimizes against **observed demand**. It does not forecast future demand.


## Overview

Transit agencies often need to balance competing objectives:

* Meeting passenger demand across routes
* Using a limited number of buses efficiently
* Avoiding unnecessary bus deployments
* Providing appropriate service frequency
* Accounting for differences in route travel/loop times

METROSAIC formulates this problem as a mixed-integer optimization model and generates an operational bus schedule based on the supplied network data.

The application provides an interactive [Streamlit](https://streamlit.io/) interface where users can either upload CSV datasets or enter a transit network directly.


## Features

* 🚍 **Bus fleet optimization** — determine which buses need to be activated.
* 🗺️ **Route assignment** — assign buses to routes for each time block.
* 📊 **Demand coverage** — ensure observed demand is covered by available transit capacity.
* ⏱️ **Loop-time adjustment** — account for differences in route loop times when calculating effective bus capacity.
* ⚖️ **Configurable optimization objectives** — adjust the tradeoff between fleet efficiency and demand allocation.
* 📁 **CSV input** — upload demand and loop-time matrices.
* ✏️ **Interactive data entry** — construct a network directly in the application.
* 📈 **Results dashboard** — view objective value, fleet utilization, route assignments, and bus schedules.
* 💾 **Downloadable results** — export assignments, route results, and fleet utilization as CSV files.


## How It Works

METROSAIC takes two primary matrices:

### 1. Demand Matrix

The demand matrix represents the number of riders expected/observed for each route during each time block.

**Rows:** Routes
**Columns:** Time blocks
**Values:** Number of riders

Example:

| Route   | Time Block 1 | Time Block 2 | Time Block 3 |
| ------- | -----------: | -----------: | -----------: |
| Route 1 |           80 |          120 |          100 |
| Route 2 |           45 |           75 |           60 |
| Route 3 |          110 |          150 |          130 |

### 2. Loop Time Matrix

The loop-time matrix represents the amount of time, in minutes, required for a bus to complete a route loop during each time block.

**Rows:** Routes
**Columns:** Time blocks
**Values:** Minutes

Example:

| Route   | Time Block 1 | Time Block 2 | Time Block 3 |
| ------- | -----------: | -----------: | -----------: |
| Route 1 |           60 |           60 |           65 |
| Route 2 |           45 |           50 |           45 |
| Route 3 |           90 |           85 |           90 |

The two matrices must have identical dimensions.

## Optimization Model

The optimization model is implemented using [Pyomo](https://www.pyomo.org/) and solved with the **CBC mixed-integer optimization solver**.

The model determines:

* Whether each available bus is activated
* Which route each bus serves during each time block
* How many buses serve each route/time combination
* Fleet utilization
* Route-level service capacity and headway

Each bus can serve at most one route during a given time block, and a bus can only be assigned if it has been activated.

### Effective Capacity

The effective capacity of a bus is adjusted based on the route loop time:

```text
Effective Capacity =
    Bus Capacity × (Time Period Length / Route Loop Time)
```

This allows the model to account for the fact that buses completing longer loops can provide fewer service cycles during the same time period.

### Objective Function

METROSAIC minimizes a weighted objective consisting of:

1. **Bus activation cost**
2. **Demand allocation penalty**

The relative importance of these objectives can be controlled through the application's **Demand Allocation Priority** setting.

* Higher priority → favors allocating additional buses toward demand.
* Lower priority → favors minimizing the number of activated buses.

The model also uses a small positive `delta` parameter when calculating the reciprocal demand allocation penalty.

## Application Parameters

The Streamlit interface exposes the following parameters:

| Parameter                      | Description                                                           |
| ------------------------------ | --------------------------------------------------------------------- |
| **Number of Buses**            | Total buses available to the network                                  |
| **Time Period Length**         | Length of each time block in minutes                                  |
| **Bus Capacity**               | Passenger capacity of an individual bus                               |
| **Bus Activation Cost**        | Cost associated with activating a bus                                 |
| **Demand Allocation Priority** | Controls the tradeoff between fleet efficiency and service allocation |
| **Delta**                      | Small positive value used in the reciprocal allocation penalty        |

The application converts the demand priority into two objective weights:

```text
Alpha = 1 - Beta
Beta  = Demand Allocation Priority / 100
```

where `Alpha` weights fleet activation cost and `Beta` weights the demand allocation component.

## Results

After optimization, METROSAIC displays several outputs.

### Summary Metrics

* Objective value
* Number of buses activated
* Total available buses
* Fleet activation percentage
* Solver status
* Termination condition

### Fleet Utilization

Shows each bus and the number of time blocks during which it is in service.

### Route Assignments

For every route/time-block combination, the application reports:

* Demand
* Number of buses assigned
* Effective capacity per bus
* Total capacity
* Surplus capacity
* Headway

### Bus Schedule

The application generates a bus-by-time-block schedule showing which route each bus serves.

### Exportable Results

Three CSV files can be downloaded directly from the application:

* `bus_assignments.csv`
* `route_results.csv`
* `fleet_utilization.csv`

## Installation

### Prerequisites

You will need:

* Python 3.x
* CBC optimization solver
* `pip`

The Python dependencies are:

```text
streamlit
pandas
numpy
pyomo
```

CBC is listed separately as a system package because Pyomo requires an external solver to execute the optimization model.

### Clone the Repository

```bash
git clone https://github.com/vmakrv/METROSAIC.git
cd METROSAIC
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Install CBC

The repository includes `coinor-cbc` in `packages.txt`.

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install coinor-cbc
```

On macOS with Homebrew:

```bash
brew install coin-or-tools/coinor/cbc
```

Verify that CBC is available:

```bash
cbc -stop
```

## Running the Application

Start the Streamlit application with:

```bash
streamlit run app.py
```

Streamlit will provide a local URL, typically:

```text
http://localhost:8501
```

## Using METROSAIC

### Option 1: Enter Data Directly

1. Start the application.
2. Select **Input Directly**.
3. Specify the number of routes.
4. Specify the number of time blocks.
5. Enter the demand matrix.
6. Enter the loop-time matrix.
7. Configure the model parameters.
8. Click **Generate Optimal Schedule**.
9. Review the optimization results.
10. Download the generated CSV files if needed.

### Option 2: Upload CSV Files

Select **Upload CSV Files** and provide:

* A demand CSV
* A loop-time CSV

Both datasets should have the same dimensions and be structured as:

```text
Rows    = Routes
Columns = Time Blocks
```

Demand values should be non-negative rider counts, while loop times must be greater than zero. These conditions are validated by the application before optimization.

## Example CSV Format

### `demand.csv`

```csv
Route,Time 1,Time 2,Time 3
1,80,120,100
2,45,75,60
3,110,150,130
```

### `loop_time.csv`

```csv
Route,Time 1,Time 2,Time 3
1,60,60,65
2,45,50,45
3,90,85,90
```

The first column is treated as part of the CSV structure when the application reads the data, so the resulting numeric matrices must have matching dimensions.

## Project Structure

```text
METROSAIC/
├── .streamlit/
├── app.py
├── optimizer.py
├── packages.txt
├── requirements.txt
└── README.md
```

### `app.py`

Contains the Streamlit user interface, including:

* Model parameter controls
* Data input
* Data validation
* Optimization execution
* Results visualization
* CSV downloads

The application calls `optimize_transit()` from `optimizer.py` to perform the underlying optimization.

### `optimizer.py`

Contains the Pyomo optimization model, including:

* Decision variables
* Constraints
* Objective function
* CBC solver configuration
* Result extraction
* Route and fleet summaries

The model uses binary variables for bus activation and route assignments and integer variables for the number of buses assigned to each route/time combination.

### `requirements.txt`

Contains the Python dependencies:

```text
streamlit
pandas
numpy
pyomo
```

### `packages.txt`

Specifies the CBC solver dependency:

```text
coinor-cbc
```

## Model Assumptions

METROSAIC currently makes several simplifying assumptions:

* Demand is treated as known observed demand rather than forecast demand.
* Each bus can serve at most one route during a time block.
* A bus must be activated before it can be assigned.
* Route demand must be fully covered by calculated effective capacity.
* Bus capacity is constant.
* Route loop time is supplied for each route/time block.
* Buses are interchangeable apart from their assignment.
* The optimization does not currently model individual vehicle locations, deadheading, driver schedules, or vehicle-specific constraints.

These assumptions make the model suitable for exploring fleet allocation and high-level transit scheduling decisions, while more detailed operational constraints could be added in future versions.

## Future Improvements

Potential extensions include:

* Demand forecasting
* Multi-depot networks
* Vehicle-specific characteristics
* Driver scheduling and labor constraints
* Deadhead and repositioning costs
* Minimum/maximum service frequencies
* Time-dependent travel times
* Multiple vehicle types
* Reliability and disruption scenarios
* Visualization of route-level service
* Sensitivity analysis
* Automated scenario comparison

## Contributing

Contributions, suggestions, and improvements are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test the application and optimization model.
5. Submit a pull request.

For larger changes, opening an issue first is recommended so the proposed approach can be discussed.

## License

No license file is currently included in the repository. If you intend for METROSAIC to be used or modified by others, consider adding an appropriate open-source license.

## Acknowledgments

METROSAIC is built with:

* [Streamlit](https://streamlit.io/) — interactive web application framework
* [Pyomo](https://www.pyomo.org/) — mathematical optimization modeling framework
* [CBC](https://github.com/coin-or/Cbc) — open-source mixed-integer programming solver
* [NumPy](https://numpy.org/) — numerical computing
* [pandas](https://pandas.pydata.org/) — data manipulation and analysis

---
**METROSAIC**
*Transit Schedule Optimizer*
