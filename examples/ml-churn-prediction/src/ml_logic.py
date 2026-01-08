"""
ML Logic for Customer Churn Prediction

This module contains the core ML pipeline logic for predicting customer churn
using Snowflake's Feature Store and Model Registry.

Pipeline Steps:
1. Feature Engineering - Create and register features in Feature Store
2. Model Training - Train sklearn model and register in Model Registry
3. Batch Inference - Run predictions and save results
"""

import logging
from snowflake.snowpark.session import Session
from snowflake.ml.registry import Registry
from snowflake.ml.feature_store import (
    FeatureStore,
    Entity,
    FeatureView,
    CreationMode
)
from sklearn.linear_model import LogisticRegression
import pandas as pd

# Set up basic logging
logger = logging.getLogger("snowflake_ml_pipeline")


def feature_engineering_task(session: Session, source_table: str, target_fs_object: str) -> str:
    """
    Step 1: Creates an Entity and Feature View in the Snowflake Feature Store.
    
    This task demonstrates how to use Snowflake's Feature Store to:
    - Define entities (the primary key for your features)
    - Create feature views with automated refresh
    - Materialize features as Dynamic Tables
    
    Args:
        session: Snowpark Session
        source_table: Input raw table (e.g. DB.SCHEMA.CUSTOMERS)
        target_fs_object: Fully qualified name for the Feature View (e.g. DB.SCHEMA.CUSTOMER_FEATURES)
    
    Returns:
        Success message with Feature View details
    """
    logger.info(f"Starting Feature Store engineering from {source_table}")
    
    # 1. Parse connection details from the target string
    try:
        parts = target_fs_object.split('.')
        if len(parts) == 3:
            db_name, schema_name, fv_name = parts
        else:
            # Fallback
            db_name = session.get_current_database()
            schema_name = session.get_current_schema()
            fv_name = target_fs_object
    except Exception:
        db_name = session.get_current_database()
        schema_name = session.get_current_schema()
        fv_name = target_fs_object

    # 2. Initialize Feature Store Client
    # Use CREATE_IF_NOT_EXIST to create Feature Store metadata if not present
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=session.get_current_warehouse(),
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )

    # 3. Define and Register Entity
    # We assume 'CUSTOMER_ID' is the primary key in the raw data
    entity_name = "CUSTOMER_ENTITY"
    customer_entity = Entity(
        name=entity_name, 
        join_keys=["CUSTOMER_ID"],
        desc="Unique Customer Identifier"
    )
    
    # Register Entity
    fs.register_entity(customer_entity)
    logger.info(f"Entity {entity_name} registered.")

    # 4. Define Feature Transformation Logic
    # Reading from the source table
    df_raw = session.table(source_table)
    
    # Perform transformations (Snowpark DataFrame operations)
    # Note: Feature Views expect the DataFrame to contain the Join Key (CUSTOMER_ID)
    df_features = df_raw.fillna(0)
    
    # 5. Define Feature View
    # A Feature View groups the logic with the Entity.
    # We set a refresh_freq to make it a Dynamic Table (automated refresh).
    fv = FeatureView(
        name=fv_name,
        entities=[customer_entity],
        feature_df=df_features,
        refresh_freq="1 day",  # Managed by Snowflake Scheduler
        desc="Customer features for Churn Prediction"
    )

    # 6. Register Feature View
    # This materializes the logic into a Dynamic Table in Snowflake
    registered_fv = fs.register_feature_view(
        feature_view=fv,
        version="v1",
        if_exists=CreationMode.CREATE_OR_OVERWRITE
    )
    
    return f"Success: Feature View {fv_name} (v1) registered in {db_name}.{schema_name}"


def model_training_task(session: Session, feature_view_path: str, model_name: str, stage_location: str) -> str:
    """
    Step 2: Reads features from Feature Store, trains model, registers in Registry.
    
    This task demonstrates how to:
    - Read features from a Feature View (materialized as Dynamic Table)
    - Train a scikit-learn model
    - Register the model in Snowflake's Model Registry
    
    Args:
        session: Snowpark Session
        feature_view_path: Path to the Feature View table
        model_name: Name for the model in the registry
        stage_location: Stage for model artifacts
    
    Returns:
        Success message with model registration details
    """
    logger.info(f"Starting Model Training using features from {feature_view_path}")
    
    # 1. Load Data
    # Since the Feature View creates a database object (Dynamic Table), 
    # we can read it directly via session.table(). 
    df_snow = session.table(feature_view_path)
    pdf = df_snow.to_pandas()
    
    if "TARGET_LABEL" not in pdf.columns:
        raise ValueError("TARGET_LABEL column missing from Feature View output")

    # Drop target and keys (CUSTOMER_ID came from Entity)
    X = pdf.drop(columns=["TARGET_LABEL", "CUSTOMER_ID"]) 
    y = pdf["TARGET_LABEL"]
    
    # 2. Train (Scikit-Learn)
    clf = LogisticRegression()
    clf.fit(X, y)
    
    # 3. Register Model using Snowflake ML Registry
    reg = Registry(session=session)
    
    # Log the model
    mv = reg.log_model(
        model=clf,
        model_name=model_name,
        version_name="v1_latest",
        conda_dependencies=["scikit-learn", "pandas"],
        comment="Logistic Regression trained on Feature Store data",
        sample_input_data=X.head()  # Good practice for signature inference
    )
    
    return f"Success: Model {model_name} trained and registered."


def inference_task(session: Session, feature_table: str, model_name: str, output_table: str) -> str:
    """
    Step 3: Loads model from registry, runs batch prediction.
    
    This task demonstrates how to:
    - Load a model from the Model Registry
    - Run batch inference using the model's run() method
    - Save predictions to an output table
    
    Args:
        session: Snowpark Session
        feature_table: Table containing features for prediction
        model_name: Name of the model in the registry
        output_table: Output table for predictions
    
    Returns:
        Success message with output table details
    """
    logger.info("Starting Batch Inference")
    
    reg = Registry(session=session)
    model_ref = reg.get_model(model_name).version("v1_latest")
    
    df_features = session.table(feature_table)
    
    # Run prediction
    result_df = model_ref.run(df_features, function_name="predict")
    
    result_df.write.mode("append").save_as_table(output_table)
    
    return f"Success: Inference saved to {output_table}"


# ============================================================================
# Main Entry Points for Stored Procedures / ML Jobs
# ============================================================================
# These functions are called by the DAG tasks. They read configuration from
# session context (database/schema) and invoke the actual task logic.

def main(session: Session) -> str:
    """
    Default main function - runs the full pipeline sequentially.
    Useful for ML Jobs mode where a single job runs everything.
    """
    db = session.get_current_database()  # e.g., DEV_ML_DB
    
    # Derive environment prefix (DEV, SIT, UAT, PRD) from current database
    env_prefix = db.split("_")[0]  # DEV_ML_DB -> DEV
    
    # Configuration - raw data is in separate database
    source_table = f"{env_prefix}_RAW_DB.PUBLIC.CUSTOMERS"
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"
    output_table = f"{db}.OUTPUT.CHURN_PREDICTIONS"
    
    # Run full pipeline
    result1 = feature_engineering_task(session, source_table, feature_view)
    logger.info(result1)
    
    result2 = model_training_task(session, feature_view, model_name, "")
    logger.info(result2)
    
    result3 = inference_task(session, feature_view, model_name, output_table)
    logger.info(result3)
    
    return "Pipeline complete"


def feature_engineering_main(session: Session) -> str:
    """Entry point for Feature Engineering stored procedure."""
    db = session.get_current_database()  # e.g., DEV_ML_DB
    
    # Derive environment prefix from current database
    env_prefix = db.split("_")[0]  # DEV_ML_DB -> DEV
    
    # Raw data is in separate database, features go to FEATURES schema
    source_table = f"{env_prefix}_RAW_DB.PUBLIC.CUSTOMERS"
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    
    return feature_engineering_task(session, source_table, feature_view)


def model_training_main(session: Session) -> str:
    """Entry point for Model Training stored procedure."""
    db = session.get_current_database()  # e.g., DEV_ML_DB
    
    # Features are in FEATURES schema
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"
    
    return model_training_task(session, feature_view, model_name, "")


def inference_main(session: Session) -> str:
    """Entry point for Inference stored procedure."""
    db = session.get_current_database()  # e.g., DEV_ML_DB
    
    # Features from FEATURES schema, output to OUTPUT schema
    feature_view = f"{db}.FEATURES.CUSTOMER_FEATURES"
    model_name = "CHURN_PREDICTION_MODEL"
    output_table = f"{db}.OUTPUT.CHURN_PREDICTIONS"
    
    return inference_task(session, feature_view, model_name, output_table)


