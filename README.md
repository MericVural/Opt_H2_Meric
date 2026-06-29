# Opt_Ammonia

Integrated, open-source techno-economic and environmental optimization framework to evaluate low-carbon fuels and other energy systems, here applied to **decentralized ammonia production**.

This repository is used for the manuscript:

> *Haber–Bosch 2.0 for low-carbon ammonia production: A global techno-economic and environmental assessment*

It provides the full modelling workflow used to evaluate more than 13,000 decentralized ammonia production configurations worldwide under grid-connected, hybrid, and off-grid system designs.

------------------------------------------------------------------------

## Overview

This framework integrates energy system modelling, techno-economic assessment, and life cycle assessment (LCA) to evaluate where, how, and under which conditions decentralized ammonia production can contribute to a low-carbon global energy system.

The framework combines:

-   **Energy system optimization (MILP-based)**
-   **Techno-economic assessment (Levelized costs of ammonia)**
-   **Spatially explicit global analysis (1° × 1° resolution)**
-   **Environmental Life Cycle Assessment (Brightway 2.5)**
-   **Prospective assessment (2050 scenarios using `premise` and IAM pathways)**

The model evaluates trade-offs between:

-   Levelized ammonia production costs (€/tNH₃)
-   Life cycle GHG emissions (tCO₂-eq/tNH₃)
-   Resource requirements (e.g., land and materials)
-   Grid dependence and decarbonization exposure
-   Operational flexibility constraints
-   Technology learning and financing assumptions

The framework is modular, scalable, and designed for large-scale
scenario analysis and high-performance computing environments.

------------------------------------------------------------------------

## System Configurations

The framework evaluates three decentralized system designs:

| Configuration     | Electricity Source         | Storage Need     | Grid Exposure |
|------------------|---------------------------|------------------|--------------|
| Grid-connected   | Grid only                 | Low–moderate     | High         |
| Hybrid           | Grid + renewables         | Moderate         | Partial      |
| Off-grid         | Renewables only           | High             | None         |

All configurations include:

-   PEM electrolytic hydrogen production;
-   Small-scale Haber-Bosch synthesis;
-   Industry-calibrated minimum-load constraints;
-   Potentially battery electricity Storage Systems and hydrogen storage;
-   Spatially explicit solar and wind yield modelling;
-   Location-specific electricity price inputs;
-   Life-cycle assessment of operational and embodied emissions.

------------------------------------------------------------------------

## Getting Started

### Install the environment

``` bash
conda env create -f lcf_opt.yml
conda activate lcf_opt
```

### Run Global Optimizations

``` bash
python 4_main_global.py
python 5_main_global_grid_connected.py
```

------------------------------------------------------------------------

## Outputs

The model provides geospatially-explicit:

-   Levelized ammonia cost (€/tNH₃);
-   Life cycle GHG emissions (tCO₂-eq/tNH₃);
-   Optimal technology capacities;
-   Storage sizing requirements;
-   Spatial maps of cost-optimal deployment.

------------------------------------------------------------------------

## Citation

If you use this framework, please cite:
> Terlouw, T., Bauer, C., Burgherr, P., McKenna, R., Rosa, L. (2026). Energy & Environmental Science. *Haber–Bosch 2.0 for low-carbon ammonia production: A global techno-economic and environmental assessment.*

------------------------------------------------------------------------

## License

See the LICENSE file for licensing details.

------------------------------------------------------------------------

## Repository Structure

The repository is organized as a modular workflow, starting from data preparation and preprocessing, followed by global optimization, post-processing, sensitivity analyses, and figure generation.

### Main workflow

| File | Description |
|------|-------------|
| **0_init_dbs_export_GHGs.ipynb** | Initializes the Brightway databases and exports life-cycle greenhouse gas emission factors used throughout the environmental assessment. |
| **1_fetch_power_prices.py** | Downloads and processes spatially explicit electricity price datasets used as optimization inputs. |
| **2_geo_plot_and_export.ipynb** | Processes geospatial datasets, visualizes intermediate results, and exports global input layers. |
| **3_main_global_preprocess.py** | Preprocesses renewable resource data, technology parameters, and optimization inputs before model execution. |
| **4_main_global.py** | Main optimization workflow for hybrid and off-grid decentralized ammonia production systems. |
| **5_main_global_grid_connected.py** | Optimization workflow for fully grid-connected ammonia production systems. |
| **6_case_studies_now_and_prospective.py** | Performs detailed present-day and prospective (2050) case study analyses. |
| **7_sensitivity_analysis_case_studies.py** | Runs sensitivity analyses for the selected case study locations. |
| **8_additional_sens_analysis.py** | Performs additional global sensitivity and uncertainty analyses reported in the manuscript. |
| **9_create_figures.ipynb** | Generates the main manuscript figures from processed optimization outputs. |
| **10_sensitivity_figures_ammonia.ipynb** | Produces publication-quality figures for the sensitivity analyses. |

### Supporting modules

| File | Purpose |
|------|---------|
| **opt_ammonia_functions.py** | Core MILP optimization model and helper routines. |
| **energy_data_processor.py** | Processing of renewable energy profiles and energy datasets. |
| **calculate_renewable_yield.py** | Calculates location-specific solar and wind yields. |
| **create_db_lca_functions.py** | Functions supporting the Brightway life-cycle assessment workflow. |
| **mapping.py** | Mapping utilities linking model outputs to environmental inventories and spatial datasets. |
| **config.py** | Central configuration file containing paths, scenarios, and model settings. |
| **lcf_opt.yml** | Conda environment specification with all required dependencies. |
| **input_data/** | Input datasets for techno-economic, geospatial, and environmental analyses. |

### Typical workflow

1. Initialize the environmental databases (`0_init_dbs_export_GHGs.ipynb`).
2. Prepare electricity price and geospatial input data (`1`–`3`).
3. Run the global optimization (`4` or `5`).
4. Perform regional case studies (`6`).
5. Conduct sensitivity analyses (`7` and `8`).
6. Generate the manuscript figures (`9` and `10`).