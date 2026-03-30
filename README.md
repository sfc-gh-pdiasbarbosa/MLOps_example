# Snowflake ML Platform - End-to-End MLOps Demo

A comprehensive, hands-on demonstration of Snowflake's complete ML platform capabilities covering every stage of the ML lifecycle: from data preparation and feature engineering through model training, registry, monitoring, explainability, lineage, serving, and distributed training.

## ML Lifecycle Coverage

| MLOps Stage | Snowflake Feature | Demo Notebook |
|---|---|---|
| Development Environment | Snowflake Notebooks on Container Runtime | All notebooks |
| Data Loading | DataConnector API | `00_data_setup` |
| Feature Engineering | Feature Store (Entity, FeatureView, Dynamic Tables) | `01_feature_engineering` |
| Model Training (Classical) | XGBoost / scikit-learn on Container Runtime | `02_model_training_xgboost` |
| Hyperparameter Tuning | Distributed GridSearchCV | `03_hyperparameter_tuning` |
| Model Registry | Versioning, Metrics, Tags, RBAC, Artifacts | `04_model_registry` |
| Batch Inference | `model_version.run()` on warehouse | `05_batch_inference` |
| ML Observability | Model Monitor (drift, performance) | `06_model_monitoring` |
| Explainability | SHAP via `model_version.run(function_name="explain")` | `07_explainability_lineage` |
| ML Lineage | End-to-end lineage (data > features > model) | `07_explainability_lineage` |
| Real-Time Serving | Model Serving on SPCS (REST API) | `08_model_serving` |
| Distributed Training | PyTorchDistributor, XGBEstimator | `09_distributed_training` |
| Orchestration | Snowflake Tasks / DAGs | `examples/ml-churn-prediction/` |
| CI/CD | GitHub Actions with environment promotion | `.github/workflows/` |

## Repository Structure

```
.
├── notebooks/                              # Interactive demo notebooks (run in SnowSight)
│   ├── 00_data_setup.ipynb                 # Data loading and exploration
│   ├── 01_feature_engineering.ipynb        # Feature Store deep dive
│   ├── 02_model_training_xgboost.ipynb     # XGBoost training with metrics
│   ├── 03_hyperparameter_tuning.ipynb      # Distributed GridSearchCV
│   ├── 04_model_registry.ipynb             # Model Registry capabilities
│   ├── 05_batch_inference.ipynb            # Batch predictions
│   ├── 06_model_monitoring.ipynb           # Drift and performance monitoring
│   ├── 07_explainability_lineage.ipynb     # SHAP values and ML lineage
│   ├── 08_model_serving.ipynb              # REST API deployment on SPCS
│   └── 09_distributed_training.ipynb       # Multi-node GPU training
│
├── examples/
│   ├── ml-churn-prediction/                # Production ML pipeline
│   │   ├── src/ml_logic.py                 # XGBoost pipeline (4 tasks)
│   │   ├── scripts/deploy_pipeline.py      # DAG deployment script
│   │   ├── config/environments.yml         # DEV/SIT/UAT/PRD config
│   │   └── README.md
│   └── quant-investment-strategy/          # Non-ML CustomModel example
│       ├── src/strategy_logic.py
│       ├── scripts/deploy_pipeline.py
│       └── README.md
│
├── sql/                                    # Infrastructure setup scripts
│   ├── 00_setup_warehouses.sql
│   ├── 01_setup_dev_environment.sql
│   ├── 02_setup_sit_environment.sql
│   ├── 02b_setup_uat_environment.sql
│   ├── 03_setup_prd_environment.sql
│   ├── 04_setup_roles_and_grants.sql
│   ├── 07_setup_monitoring.sql             # Monitoring schemas and grants
│   └── 08_setup_compute_pool.sql           # CPU/GPU compute pools
│
├── docs/
│   ├── DEMO_GUIDE.md                       # Step-by-step demo delivery guide
│   ├── SNOWFLAKE_ML_FEATURE_MAP.md         # Complete feature mapping reference
│   └── ML_VS_CUSTOM_MODELS.md              # ML vs CustomModel comparison
│
├── .github/workflows/                      # CI/CD pipelines
│   ├── ml_churn_deploy.yml
│   └── quant_strategy_deploy.yml
│
├── requirements.txt
└── README.md
```

## Quick Start

### Prerequisites

- Snowflake account with ACCOUNTADMIN access (for initial setup)
- Snowflake Notebooks enabled (Container Runtime)
- Python 3.11+ (for local development only)

### Step 1: Run SQL Setup Scripts

Execute these scripts in SnowSight SQL Worksheets in order:

```
sql/00_setup_warehouses.sql          -- Creates warehouses (XS through L)
sql/01_setup_dev_environment.sql     -- DEV databases and schemas
sql/04_setup_roles_and_grants.sql    -- ML roles and permissions
sql/07_setup_monitoring.sql          -- Monitoring schemas + lineage grants
sql/08_setup_compute_pool.sql        -- CPU/GPU compute pools
```

### Step 2: Create Demo Database

```sql
CREATE DATABASE IF NOT EXISTS MLOPS_DEMO_DB;
CREATE SCHEMA IF NOT EXISTS MLOPS_DEMO_DB.RAW;
CREATE SCHEMA IF NOT EXISTS MLOPS_DEMO_DB.FEATURES;
CREATE SCHEMA IF NOT EXISTS MLOPS_DEMO_DB.PIPELINES;
CREATE SCHEMA IF NOT EXISTS MLOPS_DEMO_DB.OUTPUT;
CREATE SCHEMA IF NOT EXISTS MLOPS_DEMO_DB.MONITORING;

CREATE WAREHOUSE IF NOT EXISTS MLOPS_DEMO_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE;
```

### Step 3: Upload and Run Notebooks

1. In SnowSight, navigate to **Projects > Notebooks**
2. Click **Import .ipynb file**
3. Upload notebooks in order (00 through 09)
4. Select **MLOPS_DEMO_DB** as the database and **MLOPS_DEMO_WH** as the warehouse
5. Run each notebook sequentially -- each builds on the previous one's outputs

## Notebooks Overview

| # | Notebook | What It Demonstrates | Key SnowSight View |
|---|----------|---------------------|-------------------|
| 00 | Data Setup | Synthetic data generation, EDA | Data > Databases > MLOPS_DEMO_DB > RAW |
| 01 | Feature Engineering | Entity, FeatureView, Dynamic Tables, point-in-time lookups | AI/ML > Feature Store |
| 02 | Model Training | XGBoost training, metric logging to registry | AI/ML > Model Registry |
| 03 | HPO | Distributed GridSearchCV, multi-version comparison | AI/ML > Model Registry (multiple versions) |
| 04 | Model Registry | Version management, tags, RBAC, artifacts | AI/ML > Model Registry > Model > Versions |
| 05 | Batch Inference | model_version.run(), prediction storage | Data > OUTPUT schema |
| 06 | Monitoring | CREATE MODEL MONITOR, drift (PSI), performance (F1) | Model Registry > Monitors tab |
| 07 | Explainability + Lineage | SHAP values, lineage graph traversal | Model Registry > Lineage tab |
| 08 | Model Serving | SPCS deployment, REST API endpoints | Model Registry > Deploy tab |
| 09 | Distributed Training | PyTorchDistributor, XGBEstimator, ML Jobs | Admin > Compute Pools |

## Production Pipeline

The `examples/ml-churn-prediction/` directory contains a production-ready pipeline with 4 chained tasks:

```
Feature Engineering >> Model Training >> Batch Inference >> Monitor Setup
```

- **Model**: XGBoost classifier for customer churn prediction
- **Orchestration**: Snowflake DAG Tasks with daily cron schedule
- **Deployment**: `deploy_pipeline.py` registers stored procedures and builds the DAG
- **CI/CD**: GitHub Actions with branch-to-environment mapping (feature/* > DEV, development > SIT, release/* > UAT, main > PRD)

## Framework Compatibility

| ML Framework | Training | Registry | Distributed | GPU |
|---|---|---|---|---|
| scikit-learn | Yes | Native | Via HPO | N/A |
| XGBoost | Yes | Native | XGBEstimator | Yes |
| LightGBM | Yes | Native | LightGBMEstimator | Yes |
| PyTorch | Yes | Native | PyTorchDistributor | Yes |
| TensorFlow / Keras | Yes | Native | Yes | Yes |
| Hugging Face | Yes | Native | Yes | Yes |
| Custom Python | Yes | CustomModel | Manual | Yes |

## Demo Delivery

For step-by-step demo instructions (including talking points and SnowSight navigation), see **[docs/DEMO_GUIDE.md](./docs/DEMO_GUIDE.md)**.

For the complete MLOps-to-Snowflake feature mapping, see **[docs/SNOWFLAKE_ML_FEATURE_MAP.md](./docs/SNOWFLAKE_ML_FEATURE_MAP.md)**.

## Resources

- [Snowflake ML Overview](https://docs.snowflake.com/en/developer-guide/snowflake-ml/overview)
- [Feature Store](https://docs.snowflake.com/en/developer-guide/snowpark-ml/feature-store/overview)
- [Model Registry](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/overview)
- [ML Observability](https://docs.snowflake.com/en/developer-guide/snowflake-ml/model-registry/model-observability)
- [ML Lineage](https://docs.snowflake.com/en/developer-guide/snowflake-ml/ml-lineage)
- [Container Runtime](https://docs.snowflake.com/en/developer-guide/snowflake-ml/container-runtime-ml)
- [Distributed Training](https://docs.snowflake.com/en/developer-guide/snowflake-ml/distributed-training)
- [End-to-End ML Workflow Quickstart](https://www.snowflake.com/en/developers/guides/end-to-end-ml-workflow/)
