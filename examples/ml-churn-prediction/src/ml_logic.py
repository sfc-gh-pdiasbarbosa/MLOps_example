"""
ML Logic for Customer Churn Prediction

This module contains the core ML pipeline logic for predicting customer churn
using Snowflake's Feature Store, Model Registry, and ML Observability.

Pipeline Steps:
1. Feature Engineering - Create and register features in Feature Store
2. Model Training - Train XGBoost model and register in Model Registry with metrics
3. Batch Inference - Run predictions and save results
4. Monitor Setup - Create or update Model Monitor for drift/performance tracking
"""

import logging
from datetime import datetime
from snowflake.snowpark.session import Session
from snowflake.snowpark import functions as F
from snowflake.ml.registry import Registry
from snowflake.ml.feature_store import (
    FeatureStore,
    Entity,
    FeatureView,
    CreationMode
)
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, precision_score, recall_score, accuracy_score, roc_auc_score
)
import pandas as pd

# Set up basic logging
logger = logging.getLogger("snowflake_ml_pipeline")


# ============================================================================
# Data Validation
# ============================================================================

def validate_data(pdf: pd.DataFrame, required_columns: list, label_column: str = None) -> dict:
    """
    Run basic data quality checks before training.

    Returns a dict with validation results. Raises ValueError on critical failures.
    """
    results = {
        "row_count": len(pdf),
        "column_count": len(pdf.columns),
        "null_counts": pdf.isnull().sum().to_dict(),
    }

    # Check required columns exist
    missing = [c for c in required_columns if c not in pdf.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Available: {list(pdf.columns)}")

    # Check minimum row count
    if len(pdf) < 50:
        raise ValueError(f"Insufficient data: {len(pdf)} rows. Minimum 50 required for training.")

    # Check class balance if label column provided
    if label_column and label_column in pdf.columns:
        class_dist = pdf[label_column].value_counts(normalize=True)
        results["class_distribution"] = class_dist.to_dict()
        minority_pct = class_dist.min()
        if minority_pct < 0.01:
            raise ValueError(f"Severe class imbalance: minority class is {minority_pct:.2%}")
        logger.info(f"Class distribution: {class_dist.to_dict()}")

    logger.info(f"Data validation passed: {len(pdf)} rows, {len(pdf.columns)} columns")
    return results


# ============================================================================
# Pipeline Tasks
# ============================================================================

def feature_engineering_task(session: Session, source_table: str, target_fs_object: str) -> str:
    """
    Step 1: Creates an Entity and Feature View in the Snowflake Feature Store.

    - Defines entities (the primary key for features)
    - Computes derived features (feature transformations)
    - Creates feature views with automated refresh via Dynamic Tables
    """
    logger.info(f"Starting Feature Store engineering from {source_table}")

    # Parse target location
    try:
        parts = target_fs_object.split('.')
        if len(parts) == 3:
            db_name, schema_name, fv_name = parts
        else:
            db_name = session.get_current_database()
            schema_name = session.get_current_schema()
            fv_name = target_fs_object
    except Exception:
        db_name = session.get_current_database()
        schema_name = session.get_current_schema()
        fv_name = target_fs_object

    # Initialize Feature Store
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=session.get_current_warehouse(),
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )

    # Define and register Entity
    customer_entity = Entity(
        name="CUSTOMER_ENTITY",
        join_keys=["CUSTOMER_ID"],
        desc="Unique Customer Identifier"
    )
    fs.register_entity(customer_entity)
    logger.info("Entity CUSTOMER_ENTITY registered.")

    # Read raw data and compute features
    df_raw = session.table(source_table)

    # Feature transformations
    df_features = df_raw.select(
        F.col("CUSTOMER_ID"),
        F.col("AGE"),
        F.col("ACCOUNT_BALANCE"),
        F.col("TENURE_MONTHS"),
        F.col("NUM_PRODUCTS"),
        F.col("HAS_CREDIT_CARD").cast("INTEGER").alias("HAS_CREDIT_CARD"),
        F.col("IS_ACTIVE_MEMBER").cast("INTEGER").alias("IS_ACTIVE_MEMBER"),
        F.col("ESTIMATED_SALARY"),
        # Derived features
        (F.col("ACCOUNT_BALANCE") / F.iff(F.col("NUM_PRODUCTS") == 0, F.lit(1), F.col("NUM_PRODUCTS"))
         ).alias("BALANCE_PER_PRODUCT"),
        (F.col("ESTIMATED_SALARY") / F.iff(F.col("ACCOUNT_BALANCE") == 0, F.lit(1), F.col("ACCOUNT_BALANCE"))
         ).alias("SALARY_BALANCE_RATIO"),
        F.iff(F.col("ACCOUNT_BALANCE") > 50000, F.lit(1), F.lit(0)).alias("IS_HIGH_VALUE"),
        # Keep label for training (will be excluded in feature retrieval for inference)
        F.col("TARGET_LABEL"),
    ).fillna(0)

    # Create and register Feature View
    fv = FeatureView(
        name=fv_name,
        entities=[customer_entity],
        feature_df=df_features,
        refresh_freq="1 day",
        desc="Customer features for churn prediction (with derived features)"
    )

    fs.register_feature_view(
        feature_view=fv,
        version="v1",
        overwrite=True
    )

    return f"Success: Feature View {fv_name} (v1) registered in {db_name}.{schema_name}"


def model_training_task(session: Session, feature_view_path: str, model_name: str, stage_location: str) -> str:
    """
    Step 2: Reads features from Feature Store, trains XGBoost, registers in Registry.

    - Loads features from the Feature View (Dynamic Table)
    - Validates data quality before training
    - Trains an XGBoost classifier
    - Registers the model in Snowflake Model Registry with metrics and tags
    - Passes sample_input_data for automatic ML Lineage capture
    """
    logger.info(f"Starting Model Training using features from {feature_view_path}")

    # Parse feature view path
    parts = feature_view_path.split(".")
    if len(parts) == 3:
        db_name, schema_name, fv_name = parts
    else:
        db_name = session.get_current_database().strip('"')
        schema_name = "FEATURES"
        fv_name = feature_view_path

    # Load data from Feature Store
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=session.get_current_warehouse().strip('"'),
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )

    fv = fs.get_feature_view(name=fv_name, version="v1")
    df_snow = fv.feature_df
    pdf = df_snow.to_pandas()

    logger.info(f"Loaded {len(pdf)} rows from feature view")

    # Data validation
    required = ["CUSTOMER_ID", "TARGET_LABEL"]
    validate_data(pdf, required_columns=required, label_column="TARGET_LABEL")

    # Prepare training data
    drop_cols = [c for c in ["TARGET_LABEL", "CUSTOMER_ID", "TIMESTAMP"] if c in pdf.columns]
    X = pdf.drop(columns=drop_cols).select_dtypes(include=["number"])
    y = pdf["TARGET_LABEL"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}, Features: {len(X.columns)}")

    # Train XGBoost
    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    y_pred_proba = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "auc_roc": round(roc_auc_score(y_test, y_pred_proba), 4),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "n_features": len(X.columns),
    }
    for k, v in metrics.items():
        logger.info(f"  {k}: {v}")

    # Register model in Snowflake Model Registry
    reg = Registry(session=session)
    version_name = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Create Snowpark DataFrame for lineage capture
    sample_input = session.create_dataframe(X_train.head(100))

    mv = reg.log_model(
        model=clf,
        model_name=model_name,
        version_name=version_name,
        conda_dependencies=["xgboost", "scikit-learn", "pandas"],
        comment=f"XGBoost classifier trained at {datetime.utcnow().isoformat()}",
        sample_input_data=sample_input,
    )

    # Log metrics
    for metric_name, metric_value in metrics.items():
        mv.set_metric(metric_name=metric_name, value=metric_value)

    logger.info(f"Model registered as {model_name} version {version_name} with {len(metrics)} metrics")

    return f"Success: Model {model_name} version {version_name} trained and registered."


def inference_task(session: Session, feature_table: str, model_name: str, output_table: str) -> str:
    """
    Step 3: Loads model from registry, runs batch prediction.

    - Loads the latest model version from the Model Registry
    - Runs batch inference using model.run()
    - Saves predictions with metadata to the output table
    """
    logger.info("Starting Batch Inference")

    # Parse feature view path
    parts = feature_table.split(".")
    if len(parts) == 3:
        db_name, schema_name, fv_name = parts
    else:
        db_name = session.get_current_database().strip('"')
        schema_name = "FEATURES"
        fv_name = feature_table

    # Get features from Feature Store
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=session.get_current_warehouse().strip('"'),
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )

    fv = fs.get_feature_view(name=fv_name, version="v1")
    df_features = fv.feature_df

    # Get model from registry (latest version)
    reg = Registry(session=session)
    model = reg.get_model(model_name)

    versions = model.versions()
    if not versions:
        raise ValueError(f"No versions found for model {model_name}")

    latest_version = versions[0]
    logger.info(f"Using model version: {latest_version.version_name}")

    # Run prediction
    result_df = latest_version.run(df_features, function_name="predict")

    # Add metadata columns
    result_df = result_df.with_column(
        "PREDICTION_TIMESTAMP", F.current_timestamp()
    ).with_column(
        "MODEL_VERSION", F.lit(latest_version.version_name)
    )

    result_df.write.mode("overwrite").save_as_table(output_table)

    row_count = session.table(output_table).count()
    logger.info(f"Predictions saved to {output_table}: {row_count} rows")

    return f"Success: Inference ({row_count} rows) saved to {output_table}"


def monitor_setup_task(session: Session, model_name: str, output_table: str, monitoring_schema: str) -> str:
    """
    Step 4: Creates or updates a Model Monitor for drift and performance tracking.

    - Prepares the monitoring source table (predictions + actuals)
    - Creates a baseline table from training data
    - Creates a Model Monitor with drift and performance tracking
    """
    logger.info("Setting up Model Monitor")

    db = session.get_current_database().strip('"')
    env_prefix = db.split("_")[0]

    # Prepare monitoring source: join predictions with actual labels
    source_table = f"{db}.{monitoring_schema}.CHURN_MONITOR_SOURCE"
    raw_table = f"{env_prefix}_RAW_DB.PUBLIC.CUSTOMERS"

    session.sql(f"""
        CREATE OR REPLACE TABLE {source_table} AS
        SELECT
            p.CUSTOMER_ID,
            p."output_feature_0"::NUMBER AS PREDICTION,
            c.TARGET_LABEL AS ACTUAL,
            p.PREDICTION_TIMESTAMP AS TIMESTAMP
        FROM {output_table} p
        JOIN {raw_table} c ON p.CUSTOMER_ID = c.CUSTOMER_ID
    """).collect()
    logger.info(f"Monitoring source table created: {source_table}")

    # Create baseline table
    baseline_table = f"{db}.{monitoring_schema}.CHURN_MONITOR_BASELINE"
    session.sql(f"""
        CREATE OR REPLACE TABLE {baseline_table} AS
        SELECT
            CUSTOMER_ID,
            TARGET_LABEL AS ACTUAL,
            0 AS PREDICTION,
            CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS TIMESTAMP
        FROM {raw_table}
        SAMPLE (80)
    """).collect()
    logger.info(f"Baseline table created: {baseline_table}")

    # Get the latest model version
    reg = Registry(session=session)
    model = reg.get_model(model_name)
    versions = model.versions()
    if not versions:
        return "Warning: No model versions found. Monitor not created."
    latest_version_name = versions[0].version_name

    # Create Model Monitor
    monitor_name = f"{db}.{monitoring_schema}.CHURN_MODEL_MONITOR"
    warehouse = session.get_current_warehouse().strip('"')

    try:
        session.sql(f"""
            CREATE OR REPLACE MODEL MONITOR {monitor_name}
            WITH
                MODEL = {db}.PIPELINES.{model_name}
                VERSION = {latest_version_name}
                FUNCTION = predict
                SOURCE = {source_table}
                BASELINE = {baseline_table}
                TIMESTAMP_COLUMN = TIMESTAMP
                PREDICTION_CLASS_COLUMNS = (PREDICTION)
                ACTUAL_CLASS_COLUMNS = (ACTUAL)
                ID_COLUMNS = (CUSTOMER_ID)
                WAREHOUSE = {warehouse}
                REFRESH_INTERVAL = '1 hour'
                AGGREGATION_WINDOW = '1 day'
        """).collect()
        logger.info(f"Model Monitor created: {monitor_name}")
        return f"Success: Model Monitor {monitor_name} created for version {latest_version_name}"
    except Exception as e:
        logger.warning(f"Monitor creation failed (may already exist or feature not available): {e}")
        return f"Warning: Monitor setup encountered an issue: {e}"


# ============================================================================
# Main Entry Points for Stored Procedures / ML Jobs
# ============================================================================

def main(session: Session) -> str:
    """
    Default main function - runs the full pipeline sequentially.
    Useful for ML Jobs mode where a single job runs everything.
    """
    db = session.get_current_database().strip('"')
    env_prefix = db.split("_")[0]

    source_table = f"{env_prefix}_RAW_DB.PUBLIC.CUSTOMERS"
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"
    output_table = f"{db}.OUTPUT.CHURN_PREDICTIONS"
    monitoring_schema = "MONITORING"

    result1 = feature_engineering_task(session, source_table, feature_view)
    logger.info(result1)

    result2 = model_training_task(session, feature_view, model_name, "")
    logger.info(result2)

    result3 = inference_task(session, feature_view, model_name, output_table)
    logger.info(result3)

    result4 = monitor_setup_task(session, model_name, output_table, monitoring_schema)
    logger.info(result4)

    return "Pipeline complete"


def feature_engineering_main(session: Session) -> str:
    """Entry point for Feature Engineering stored procedure."""
    db_raw = session.get_current_database()
    if db_raw is None:
        result = session.sql("SELECT CURRENT_DATABASE()").collect()
        db = result[0][0] if result else "DEV_ML_DB"
    else:
        db = db_raw.strip('"')

    env_prefix = db.split("_")[0]
    source_table = f"{env_prefix}_RAW_DB.PUBLIC.CUSTOMERS"
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"

    return feature_engineering_task(session, source_table, feature_view)


def model_training_main(session: Session) -> str:
    """Entry point for Model Training stored procedure."""
    db_raw = session.get_current_database()
    if db_raw is None:
        result = session.sql("SELECT CURRENT_DATABASE()").collect()
        db = result[0][0] if result else "DEV_ML_DB"
    else:
        db = db_raw.strip('"')

    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"

    return model_training_task(session, feature_view, model_name, "")


def inference_main(session: Session) -> str:
    """Entry point for Inference stored procedure."""
    db_raw = session.get_current_database()
    if db_raw is None:
        result = session.sql("SELECT CURRENT_DATABASE()").collect()
        db = result[0][0] if result else "DEV_ML_DB"
    else:
        db = db_raw.strip('"')

    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"
    output_table = f"{db}.OUTPUT.CHURN_PREDICTIONS"

    return inference_task(session, feature_view, model_name, output_table)


def monitor_setup_main(session: Session) -> str:
    """Entry point for Monitor Setup stored procedure."""
    db_raw = session.get_current_database()
    if db_raw is None:
        result = session.sql("SELECT CURRENT_DATABASE()").collect()
        db = result[0][0] if result else "DEV_ML_DB"
    else:
        db = db_raw.strip('"')

    model_name = "CHURN_PREDICTION_MODEL"
    output_table = f"{db}.OUTPUT.CHURN_PREDICTIONS"
    monitoring_schema = "MONITORING"

    return monitor_setup_task(session, model_name, output_table, monitoring_schema)
