"""
ML Pipeline Deployment Script for Customer Churn Prediction

This script deploys the ML retraining pipeline to Snowflake.
It creates stored procedures and orchestrates them via Tasks.

Pipeline Tasks:
1. Feature Engineering - Updates Feature Store
2. Model Training - Retrains and registers model
3. Batch Inference - Runs predictions

Usage:
    python deploy_pipeline.py <ENV_NAME>
    
Example:
    python deploy_pipeline.py DEV
"""

import os
import yaml
import sys
from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc
from snowflake.snowpark.types import StringType

# Add src to path to import logic definitions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


def get_snowpark_session():
    """
    Creates a session using Key Pair authentication.
    """
    connection_params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "private_key": os.environ["SNOWFLAKE_PRIVATE_KEY"], 
        "role": os.environ["SNOWFLAKE_ROLE"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "schema": os.environ["SNOWFLAKE_SCHEMA"]
    }
    return Session.builder.configs(connection_params).create()


def deploy(env_name: str):
    """
    Deploy the ML pipeline to the specified environment.
    
    Args:
        env_name: Target environment (DEV, SIT, UAT, PRD)
    """
    print(f"--- Deploying ML Pipeline to Environment: {env_name} ---")
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'environments.yml')
    with open(config_path, "r") as f:
        full_config = yaml.safe_load(f)
    
    env_config = full_config[env_name].copy()
    env_config.update(full_config['default']) 
    
    session = get_snowpark_session()
    
    db_name = env_config['database']
    schema_name = env_config['schema']
    wh_name = env_config['warehouse']
    
    # Table names from config
    raw_data_table = env_config['tables']['raw_data']
    feature_store_table = env_config['tables']['feature_store']
    inference_output_table = env_config['tables']['inference_output']
    model_name = env_config['model_name']
    
    # Stage locations
    code_stage = f"{db_name}.{schema_name}.ML_CODE_STAGE"
    
    print(f"Target: {db_name}.{schema_name}")
    print(f"Warehouse: {wh_name}")
    
    # Upload ML logic to stage
    print("Uploading ML logic to stage...")
    ml_logic_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'ml_logic.py')
    session.file.put(
        ml_logic_path,
        f"@{code_stage}",
        auto_compress=False,
        overwrite=True
    )
    print("✅ ML logic uploaded to stage")
    
    # ========================================
    # Create Stored Procedures
    # ========================================
    
    print("Creating stored procedures...")
    
    # Feature Engineering Stored Procedure
    fe_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_FEATURE_ENGINEERING()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/ml_logic.py')
    HANDLER = 'run_feature_engineering'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_feature_engineering(session: Session) -> str:
    import ml_logic
    return ml_logic.feature_engineering_task(
        session, 
        '{raw_data_table}', 
        '{feature_store_table}'
    )
    $$;
    """
    session.sql(fe_sproc_sql).collect()
    print("  ✅ SP_FEATURE_ENGINEERING created")
    
    # Model Training Stored Procedure
    train_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_MODEL_TRAINING()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'scikit-learn', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/ml_logic.py')
    HANDLER = 'run_model_training'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_model_training(session: Session) -> str:
    import ml_logic
    return ml_logic.model_training_task(
        session,
        '{feature_store_table}',
        '{model_name}'
    )
    $$;
    """
    session.sql(train_sproc_sql).collect()
    print("  ✅ SP_MODEL_TRAINING created")
    
    # Inference Stored Procedure
    infer_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_INFERENCE()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/ml_logic.py')
    HANDLER = 'run_inference'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_inference(session: Session) -> str:
    import ml_logic
    return ml_logic.inference_task(
        session,
        '{feature_store_table}',
        '{model_name}',
        '{inference_output_table}'
    )
    $$;
    """
    session.sql(infer_sproc_sql).collect()
    print("  ✅ SP_INFERENCE created")
    
    # ========================================
    # Create Tasks (DAG)
    # ========================================
    
    print("Creating task DAG...")
    
    # Root task - Feature Engineering (runs on schedule)
    root_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_FEATURE_ENGINEERING
        WAREHOUSE = {wh_name}
        SCHEDULE = 'USING CRON 0 2 * * * UTC'
        COMMENT = 'ML Pipeline: Feature Engineering Task'
    AS
        CALL {db_name}.{schema_name}.SP_FEATURE_ENGINEERING();
    """
    session.sql(root_task_sql).collect()
    print("  ✅ TASK_FEATURE_ENGINEERING created")
    
    # Training task - depends on feature engineering
    train_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_MODEL_TRAINING
        WAREHOUSE = {wh_name}
        AFTER {db_name}.{schema_name}.TASK_FEATURE_ENGINEERING
        COMMENT = 'ML Pipeline: Model Training Task'
    AS
        CALL {db_name}.{schema_name}.SP_MODEL_TRAINING();
    """
    session.sql(train_task_sql).collect()
    print("  ✅ TASK_MODEL_TRAINING created")
    
    # Inference task - depends on training
    infer_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_INFERENCE
        WAREHOUSE = {wh_name}
        AFTER {db_name}.{schema_name}.TASK_MODEL_TRAINING
        COMMENT = 'ML Pipeline: Batch Inference Task'
    AS
        CALL {db_name}.{schema_name}.SP_INFERENCE();
    """
    session.sql(infer_task_sql).collect()
    print("  ✅ TASK_INFERENCE created")
    
    # ========================================
    # Resume or Execute Tasks
    # ========================================
    
    if env_name == 'PRD':
        print("Environment is PRD: Resuming task schedule...")
        # Resume tasks in reverse dependency order
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_INFERENCE RESUME").collect()
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_MODEL_TRAINING RESUME").collect()
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_FEATURE_ENGINEERING RESUME").collect()
        print("✅ Tasks resumed - pipeline will run on schedule")
    else:
        print(f"Environment is {env_name}: Tasks created but suspended.")
        print("To run manually, execute:")
        print(f"  EXECUTE TASK {db_name}.{schema_name}.TASK_FEATURE_ENGINEERING;")
    
    print("\n✅ ML Pipeline deployment complete!")
    session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_pipeline.py <ENV_NAME>")
        print("Example: python deploy_pipeline.py DEV")
        sys.exit(1)
    
    target_env = sys.argv[1]
    deploy(target_env)
