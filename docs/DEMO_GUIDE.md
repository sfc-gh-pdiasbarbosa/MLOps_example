# Demo Guide: End-to-End MLOps on Snowflake

Step-by-step instructions for delivering the MLOps demo. Each section corresponds to a notebook in the `notebooks/` directory.

---

## Pre-Demo Setup

### 1. Run SQL Setup Scripts

Execute the following SQL scripts in SnowSight (as ACCOUNTADMIN) in order:

```
sql/00_setup_warehouses.sql
sql/01_setup_dev_environment.sql
sql/04_setup_roles_and_grants.sql
sql/07_setup_monitoring.sql
sql/08_setup_compute_pool.sql
```

### 2. Upload Notebooks to Snowflake

1. In SnowSight, navigate to **Projects > Notebooks**
2. Click **+ Notebook** > **Import .ipynb file**
3. Upload all files from `notebooks/` in order (00 through 09)
4. For each notebook, select:
   - **Database**: MLOPS_DEMO_DB (or create during notebook 00)
   - **Warehouse**: MLOPS_DEMO_WH
   - **Runtime**: For notebooks 00-08, use a standard CPU runtime. For notebook 09 (distributed training), select a GPU-enabled runtime if available.

### 3. Verify Account Features

The demo uses these Snowflake features. Verify they are available in the account:
- Feature Store (GA)
- Model Registry (GA)
- ML Observability / Model Monitors (GA)
- ML Lineage (GA)
- Container Runtime (GA)
- Compute Pools (for notebooks 08 and 09)

---

## Demo Flow

### Opening (2 min)

Set the context: "We are going to walk through a complete ML workflow — from raw data to production monitoring — using Snowflake's native ML platform. Everything runs inside Snowflake. No data leaves the platform."

---

### Step 0: Data Setup (notebook 00)

**What to run**: Execute all cells.

**What to show in SnowSight**:
- Navigate to **MLOPS_DEMO_DB > RAW > CUSTOMERS**
- Show the data preview (5000 rows of synthetic customer data)
- Point out that CHANGE_TRACKING = TRUE is enabled (required for Feature Store Dynamic Tables)

**Key message**: Raw data lives in Snowflake. This is the starting point.

---

### Step 1: Feature Engineering (notebook 01)

**What to run**: Execute all cells.

**What to show in SnowSight**:
- Navigate to **AI/ML > Feature Store**
- Click on **CUSTOMER_FEATURES** entity
- Show the FeatureView with its refresh schedule
- Click into the Dynamic Table backing the feature view
- Show the automatic refresh history

**Key message**: Feature Store centralizes feature definitions. Features are backed by Dynamic Tables that Snowflake refreshes automatically — no external scheduler needed. This replaces the need for separate feature engineering pipelines.

---

### Step 2: Model Training (notebook 02)

**What to run**: Execute all cells. Highlight the XGBoost training and metric computation.

**What to show in SnowSight**:
- Navigate to **AI/ML > Model Registry**
- Click on **CHURN_PREDICTION**
- Show the **xgb_baseline** version
- Click into metrics — show accuracy, F1, precision, recall, AUC
- Show the **Lineage** tab — the graph from RAW.CUSTOMERS to CUSTOMER_FEATURES to the model

**Key message**: XGBoost runs natively in Snowflake. The model is registered as a first-class object with version control, metrics, and automatic lineage. The registry supports scikit-learn, XGBoost, LightGBM, PyTorch, TensorFlow, and custom models.

---

### Step 3: Hyperparameter Tuning (notebook 03)

**What to run**: Execute all cells. The GridSearchCV will take a few minutes — this is a good time to explain the distributed execution.

**What to show in SnowSight**:
- While HPO runs, show the **Query History** — multiple parallel queries executing
- After completion, go to **Model Registry** and show the new **xgb_optimized** version
- Compare metrics between baseline and optimized versions

**Key message**: Hyperparameter optimization is distributed across warehouse nodes automatically. No code changes needed — same scikit-learn API.

---

### Step 4: Model Registry Deep Dive (notebook 04)

**What to run**: Execute all cells. This is an exploration notebook.

**What to show in SnowSight**:
- Model Registry: version list, metrics comparison
- Files tab: show the model artifacts stored in Snowflake
- Demonstrate the SQL interface: `SHOW MODELS`
- Show that RBAC applies: `GRANT USAGE ON MODEL ... TO ROLE ...`

**Key message**: The Model Registry is not just storage — it is a governed, versioned, auditable system. Models are schema-level objects with full RBAC.

---

### Step 5: Batch Inference (notebook 05)

**What to run**: Execute all cells.

**What to show in SnowSight**:
- Navigate to **MLOPS_DEMO_DB > OUTPUT > CHURN_PREDICTIONS**
- Show the prediction results
- Point out MODEL_VERSION and PREDICTION_TIMESTAMP columns

**Key message**: Inference runs on Snowflake compute. `model.run()` is a vectorized function — it scales with warehouse size. No data movement.

---

### Step 6: ML Observability (notebook 06)

**What to run**: Execute all cells. The Model Monitor creation is the highlight.

**What to show in SnowSight**:
- Navigate to **AI/ML > Model Registry > CHURN_PREDICTION > xgb_optimized**
- Click the **Monitors** tab
- Show the monitoring dashboard: drift charts, performance charts
- Explain the refresh interval and aggregation window

**Key message**: Snowflake provides built-in model monitoring. No external tools needed. You get drift detection, performance tracking, and volume monitoring out of the box. Metrics are queryable via SQL for integration with alerting systems.

---

### Step 7: Explainability and Lineage (notebook 07)

**What to run**: Execute all cells.

**What to show in SnowSight**:
- Model Registry > CHURN_PREDICTION > xgb_optimized > **Lineage** tab
- Show the full graph: RAW.CUSTOMERS → CUSTOMER_FEATURES → CHURN_PREDICTION
- Feature Store > CUSTOMER_FEATURES > **Lineage** tab (shows downstream models)

**Key message**: SHAP values are computed natively — one API call. ML Lineage traces the complete data flow automatically. This is critical for governance, compliance, and debugging.

---

### Step 8: Model Serving (notebook 08)

**What to run**: Execute all cells. Note that SPCS deployment requires a compute pool — the notebook explains both the API approach and the SnowSight UI approach.

**What to show in SnowSight**:
- Model Registry > CHURN_PREDICTION > xgb_optimized > **Deploy** button
- Walk through the deployment dialog (compute pool, service name, ingress)
- Explain that this creates a REST API endpoint

**Key message**: Models can be served as REST API endpoints for real-time inference. The same model from the registry — no re-packaging, no Docker images to build.

---

### Step 9: Distributed Training (notebook 09)

**What to run**: Walk through the code cells (some may need a GPU compute pool to execute). The API patterns are the focus, not necessarily live execution.

**What to show in SnowSight**:
- Admin > Compute Pools — show available CPU and GPU pools
- Notebook settings — show runtime selection (CPU vs GPU)

**Key message**: Snowflake supports distributed training with XGBoost, LightGBM, and PyTorch out of the box. Multi-node GPU training is managed by Snowflake — no Ray cluster to set up, no Docker images to build, no infrastructure to manage. Data scientists use familiar APIs (PyTorch DDP, XGBoost) with minimal modifications.

---

### Closing (2 min)

Summarize what was demonstrated:

1. **Feature Store** — centralized, automated feature engineering
2. **Model Training** — XGBoost, PyTorch, distributed HPO, GPU support
3. **Model Registry** — version control, metrics, tags, RBAC, artifacts
4. **Batch and Real-Time Inference** — warehouse-based and SPCS-based
5. **ML Observability** — drift detection, performance monitoring, alerting
6. **Explainability** — built-in SHAP values
7. **ML Lineage** — end-to-end data flow tracing
8. **Governance** — RBAC, audit trail, compliance

All of this runs natively in Snowflake. No data leaves the platform. No external tools required for any step of the ML lifecycle.

---

## Troubleshooting

| Issue | Resolution |
|---|---|
| Feature Store errors on CREATE | Ensure CHANGE_TRACKING = TRUE on source tables |
| Model Monitor creation fails | Ensure TIMESTAMP column is TIMESTAMP_NTZ type |
| Distributed training timeout | Increase compute pool MAX_NODES |
| Model serving deployment fails | Verify compute pool exists and role has USAGE grant |
| ML Lineage empty | Lineage is captured at object creation time. Re-run the pipeline if objects were created before lineage was enabled |
| GridSearchCV slow | Use a larger warehouse (M or L) for HPO workloads |

## References

- [Snowflake ML Feature Map](SNOWFLAKE_ML_FEATURE_MAP.md) — complete feature mapping table
- [End-to-End ML Workflow Quickstart](https://www.snowflake.com/en/developers/guides/end-to-end-ml-workflow/)
- [Snowflake ML Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-ml/overview)
