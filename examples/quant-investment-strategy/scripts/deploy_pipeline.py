"""
Investment Strategy Pipeline Deployment Script (Non-ML Example)

This script deploys the quantitative investment strategy pipeline to Snowflake.
It demonstrates that Snowflake's ML platform features (Tasks, Model Registry, 
Feature Store) work equally well with non-ML mathematical models.

Pipeline Tasks:
1. Feature Engineering - Calculate technical indicators
2. Strategy Registration - Register the custom model
3. Signal Generation - Generate trading signals

Usage:
    python deploy_pipeline.py <ENV_NAME>
    
Example:
    python deploy_pipeline.py DEV
"""

import os
import yaml
import sys
from snowflake.snowpark import Session

# Add src to path to import strategy logic
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
    Deploy the investment strategy pipeline to the specified environment.
    
    This pipeline differs from ML pipelines:
    - No "training" task (strategy is rule-based, not learned)
    - Strategy registration is more like "publishing" than "training"
    - More frequent refresh for real-time trading scenarios
    
    Args:
        env_name: Target environment (DEV, SIT, UAT, PRD)
    """
    print(f"--- Deploying Investment Strategy Pipeline to Environment: {env_name} ---")
    
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
    signals_output_table = env_config['tables']['signals_output']
    strategy_name = env_config['strategy_name']
    
    # Stage locations
    code_stage = f"{db_name}.{schema_name}.STRATEGY_CODE_STAGE"
    
    print(f"Target: {db_name}.{schema_name}")
    print(f"Warehouse: {wh_name}")
    
    # Upload strategy logic to stage
    print("Uploading strategy logic to stage...")
    strategy_logic_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'strategy_logic.py')
    session.file.put(
        strategy_logic_path,
        f"@{code_stage}",
        auto_compress=False,
        overwrite=True
    )
    print("✅ Strategy logic uploaded to stage")
    
    # ========================================
    # Create Stored Procedures
    # ========================================
    
    print("Creating stored procedures...")
    
    # Feature Engineering (Technical Indicators) Stored Procedure
    fe_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_CALCULATE_INDICATORS()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'numpy', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/strategy_logic.py')
    HANDLER = 'run_feature_engineering'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_feature_engineering(session: Session) -> str:
    import strategy_logic
    return strategy_logic.feature_engineering_task(
        session, 
        '{raw_data_table}', 
        '{feature_store_table}'
    )
    $$;
    """
    session.sql(fe_sproc_sql).collect()
    print("  ✅ SP_CALCULATE_INDICATORS created")
    
    # Strategy Registration Stored Procedure
    register_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_REGISTER_STRATEGY()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'numpy', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/strategy_logic.py')
    HANDLER = 'run_strategy_registration'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_strategy_registration(session: Session) -> str:
    import strategy_logic
    return strategy_logic.strategy_registration_task(
        session,
        '{feature_store_table}',
        '{strategy_name}'
    )
    $$;
    """
    session.sql(register_sproc_sql).collect()
    print("  ✅ SP_REGISTER_STRATEGY created")
    
    # Signal Generation Stored Procedure
    signals_sproc_sql = f"""
    CREATE OR REPLACE PROCEDURE {db_name}.{schema_name}.SP_GENERATE_SIGNALS()
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'numpy', 'snowflake-ml-python')
    IMPORTS = ('@{code_stage}/strategy_logic.py')
    HANDLER = 'run_signal_generation'
    AS
    $$
import pandas as pd
from snowflake.snowpark import Session

def run_signal_generation(session: Session) -> str:
    import strategy_logic
    return strategy_logic.signal_generation_task(
        session,
        '{feature_store_table}',
        '{strategy_name}',
        '{signals_output_table}'
    )
    $$;
    """
    session.sql(signals_sproc_sql).collect()
    print("  ✅ SP_GENERATE_SIGNALS created")
    
    # ========================================
    # Create Tasks (DAG)
    # ========================================
    
    print("Creating task DAG...")
    
    # Root task - Calculate Indicators (runs on schedule - hourly for trading)
    root_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_CALCULATE_INDICATORS
        WAREHOUSE = {wh_name}
        SCHEDULE = 'USING CRON 0 * * * * UTC'
        COMMENT = 'Investment Strategy Pipeline: Calculate Technical Indicators'
    AS
        CALL {db_name}.{schema_name}.SP_CALCULATE_INDICATORS();
    """
    session.sql(root_task_sql).collect()
    print("  ✅ TASK_CALCULATE_INDICATORS created")
    
    # Register Strategy task - depends on indicators
    register_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_REGISTER_STRATEGY
        WAREHOUSE = {wh_name}
        AFTER {db_name}.{schema_name}.TASK_CALCULATE_INDICATORS
        COMMENT = 'Investment Strategy Pipeline: Register Strategy in Model Registry'
    AS
        CALL {db_name}.{schema_name}.SP_REGISTER_STRATEGY();
    """
    session.sql(register_task_sql).collect()
    print("  ✅ TASK_REGISTER_STRATEGY created")
    
    # Generate Signals task - depends on registration
    signals_task_sql = f"""
    CREATE OR REPLACE TASK {db_name}.{schema_name}.TASK_GENERATE_SIGNALS
        WAREHOUSE = {wh_name}
        AFTER {db_name}.{schema_name}.TASK_REGISTER_STRATEGY
        COMMENT = 'Investment Strategy Pipeline: Generate Trading Signals'
    AS
        CALL {db_name}.{schema_name}.SP_GENERATE_SIGNALS();
    """
    session.sql(signals_task_sql).collect()
    print("  ✅ TASK_GENERATE_SIGNALS created")
    
    # ========================================
    # Resume or Execute Tasks
    # ========================================
    
    if env_name == 'PRD':
        print("Environment is PRD: Resuming task schedule (hourly)...")
        # Resume tasks in reverse dependency order
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_GENERATE_SIGNALS RESUME").collect()
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_REGISTER_STRATEGY RESUME").collect()
        session.sql(f"ALTER TASK {db_name}.{schema_name}.TASK_CALCULATE_INDICATORS RESUME").collect()
        print("✅ Tasks resumed - pipeline will run hourly")
    else:
        print(f"Environment is {env_name}: Tasks created but suspended.")
        print("To run manually, execute:")
        print(f"  EXECUTE TASK {db_name}.{schema_name}.TASK_CALCULATE_INDICATORS;")
    
    print("\n✅ Investment Strategy Pipeline deployment complete!")
    session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_pipeline.py <ENV_NAME>")
        print("Example: python deploy_pipeline.py DEV")
        sys.exit(1)
    
    target_env = sys.argv[1]
    deploy(target_env)
