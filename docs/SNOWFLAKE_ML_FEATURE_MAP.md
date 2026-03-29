# Snowflake ML Feature Map

A reference mapping every stage of the ML lifecycle to the Snowflake feature that addresses it.

## MLOps Lifecycle Coverage

| MLOps Stage | Snowflake Feature | How It Works |
|---|---|---|
| **Development Environment** | Snowflake Notebooks on Container Runtime | Jupyter-compatible environment with pre-installed ML packages (PyTorch, XGBoost, scikit-learn, TensorFlow). CPU and GPU compute available. No infrastructure management. |
| **Data Loading** | DataConnector API | Optimized, distributed data ingestion from Snowflake tables directly into pandas DataFrames, PyTorch datasets, or TensorFlow datasets. Significantly faster than `.to_pandas()` for large datasets. |
| **Feature Engineering** | Feature Store (Entity + FeatureView) | Centralized feature definitions backed by Dynamic Tables. Automated refresh on configurable schedules. Point-in-time lookups via spine DataFrames. Feature versioning. |
| **Model Training (Classical ML)** | Container Runtime (CPU) | XGBoost, LightGBM, scikit-learn running on managed warehouse or Container Runtime compute. No UDF wrapping required. |
| **Model Training (Deep Learning)** | Container Runtime (GPU) | PyTorch, TensorFlow, Keras on GPU-enabled compute pools. Pre-installed packages, pip extensible. |
| **Hyperparameter Tuning** | Distributed GridSearchCV / RandomSearchCV | `snowflake.ml.modeling.model_selection.GridSearchCV` — parallelized across warehouse nodes. Also supports optuna and hyperopt. |
| **Distributed Training** | PyTorchDistributor, XGBEstimator, LightGBMEstimator | Multi-node, multi-GPU training on compute pools. Automatic resource discovery. Ray-backed cluster (no user config). |
| **Datasets** | Snowflake Datasets | Immutable, versioned data snapshots optimized for ML ingestion. Integrates with Feature Store for point-in-time correct training sets. |
| **Model Registry** | Snowflake Model Registry | Schema-level objects with version control, metric tracking, tags, artifact storage, RBAC, and automatic lineage capture. Supports sklearn, XGBoost, LightGBM, PyTorch, TensorFlow, Hugging Face, and custom models. |
| **Batch Inference** | `model_version.run()` | Scalable batch predictions executed on Snowflake warehouses. Vectorized execution. No data movement. |
| **Real-Time Inference** | Model Serving on SPCS | Deploy models from the registry to Snowpark Container Services with auto-generated REST API endpoints. Auto-scaling containers. |
| **ML Observability** | Model Monitor (`CREATE MODEL MONITOR`) | Automated drift detection (PSI, KL divergence, difference of means), performance tracking (F1, precision, recall, AUC), and volume monitoring. Configurable refresh intervals. SnowSight dashboard. |
| **Explainability** | SHAP via `model_version.run(function_name="explain")` | Built-in Shapley value computation for any model in the registry. No additional packages required. |
| **ML Lineage** | ML Lineage API | End-to-end tracing from source tables through feature views, datasets, to registered models and deployed services. Queryable via Python API, SQL, and visible in SnowSight UI. |
| **Orchestration** | Snowflake Tasks / DAGs | Native pipeline orchestration with cron scheduling, dependency chaining, error handling. Python DAG API for programmatic construction. |
| **ML Jobs** | ML Jobs on Container Runtime | Remote execution of Python ML workloads on compute pools. Integrates with Tasks for scheduled execution and with external orchestrators (Airflow, Prefect). |
| **Governance** | RBAC, Tags, Audit Trail | Role-based access control on models, features, and data. Model tagging for lifecycle management. Full audit trail via ACCESS_HISTORY. |
| **CI/CD** | GitHub Actions + Snowflake CLI | Automated testing and deployment across environments (DEV/SIT/UAT/PRD). Branch-based environment mapping. |

## Framework Compatibility

| ML Framework | Training | Registry Support | Distributed | GPU |
|---|---|---|---|---|
| scikit-learn | Yes | Native | Via HPO | N/A |
| XGBoost | Yes | Native | Yes (XGBEstimator) | Yes |
| LightGBM | Yes | Native | Yes (LightGBMEstimator) | Yes |
| PyTorch | Yes | Native | Yes (PyTorchDistributor) | Yes |
| TensorFlow / Keras | Yes | Native | Yes | Yes |
| Hugging Face | Yes | Native (pipeline) | Yes | Yes |
| CatBoost | Yes | Native | Manual | N/A |
| Prophet | Yes | Native | Manual | N/A |
| Custom Python | Yes | Via CustomModel | Manual | Yes |

## SnowSight UI Navigation

| Feature | SnowSight Path |
|---|---|
| Feature Store | AI/ML > Feature Store |
| Model Registry | AI/ML > Model Registry |
| Model Monitors | AI/ML > Model Registry > [Model] > [Version] > Monitors |
| ML Lineage | AI/ML > Model Registry > [Model] > [Version] > Lineage |
| Model Artifacts | AI/ML > Model Registry > [Model] > [Version] > Files |
| Model Serving | AI/ML > Model Registry > [Model] > [Version] > Deploy |
| Compute Pools | Admin > Compute Pools |
| Tasks / DAGs | Data > Databases > [DB] > [Schema] > Tasks |
| Notebooks | Projects > Notebooks |

## Resources

- [Snowflake ML Overview](https://docs.snowflake.com/en/developer-guide/snowflake-ml/overview)
- [Feature Store Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/feature-store/overview)
- [Model Registry Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/model-registry/overview)
- [ML Observability Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/model-registry/model-observability)
- [ML Lineage Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/ml-lineage)
- [Container Runtime Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/container-runtime-ml)
- [Distributed Training Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/distributed-training)
- [End-to-End ML Workflow Quickstart](https://www.snowflake.com/en/developers/guides/end-to-end-ml-workflow/)
