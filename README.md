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