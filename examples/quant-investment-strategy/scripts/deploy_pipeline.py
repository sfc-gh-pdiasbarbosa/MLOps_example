"""
Investment Strategy Pipeline Deployment Script (Non-ML Example)

This script deploys the quantitative investment strategy pipeline to Snowflake.
It demonstrates that Snowflake's ML platform features (DAGs, Model Registry, 
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
from datetime import timedelta
from snowflake.snowpark import Session
from snowflake.core import Root
from snowflake.core.task.dagv1 import DAG, DAGTask, DAGOperation
from snowflake.core.task.context import StoredProcedureCall

# Add src to path to import strategy logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import strategy_logic


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
    Deploy the investment strategy pipeline DAG to the specified environment.
    
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
    root = Root(session)
    
    schema_name = env_config['schema']
    db_name = env_config['database']
    wh_name = env_config['warehouse']
    
    # Stage locations
    code_stage = f"@{db_name}.{schema_name}.STRATEGY_CODE_STAGE"
    model_stage = f"@{db_name}.{schema_name}.STRATEGY_MODELS_STAGE"

    dag_name = "INVESTMENT_STRATEGY_PIPELINE"
    
    print("Defining DAG structure...")
    
    # Note: This DAG runs more frequently than ML pipelines
    # Trading strategies often need hourly or even more frequent updates
    with DAG(dag_name, schedule=timedelta(hours=1), warehouse=wh_name) as dag:
        
        # --- Task 1: Feature Engineering (Technical Indicators) ---
        # This is similar to ML feature engineering, but calculates
        # mathematical indicators instead of ML features
        task_fe = DAGTask(
            "TASK_CALCULATE_INDICATORS",
            StoredProcedureCall(
                strategy_logic.feature_engineering_task,
                args=[
                    env_config['tables']['raw_data'],
                    env_config['tables']['feature_store']
                ],
                stage_location=code_stage,
                packages=[
                    "snowflake-snowpark-python", 
                    "pandas", 
                    "numpy",
                    "snowflake-ml-python"
                ],
                imports=[f"{code_stage}/strategy_logic.py"]
            ),
            warehouse=wh_name
        )

        # --- Task 2: Strategy Registration ---
        # This replaces "training" in ML pipelines
        # The strategy is registered/updated in the Model Registry
        # even though it's not an ML model
        task_register = DAGTask(
            "TASK_REGISTER_STRATEGY",
            StoredProcedureCall(
                strategy_logic.strategy_registration_task,
                args=[
                    env_config['tables']['feature_store'],
                    env_config['strategy_name'],
                    model_stage
                ],
                stage_location=code_stage,
                packages=[
                    "snowflake-snowpark-python", 
                    "pandas", 
                    "numpy",
                    "snowflake-ml-python"
                ],
                imports=[f"{code_stage}/strategy_logic.py"]
            ),
            warehouse=wh_name
        )

        # --- Task 3: Signal Generation ---
        # This is analogous to "inference" in ML pipelines
        task_signals = DAGTask(
            "TASK_GENERATE_SIGNALS",
            StoredProcedureCall(
                strategy_logic.signal_generation_task,
                args=[
                    env_config['tables']['feature_store'],
                    env_config['strategy_name'],
                    env_config['tables']['signals_output']
                ],
                stage_location=code_stage,
                packages=[
                    "snowflake-snowpark-python", 
                    "pandas", 
                    "numpy",
                    "snowflake-ml-python"
                ],
                imports=[f"{code_stage}/strategy_logic.py"]
            ),
            warehouse=wh_name
        )

        # Define dependencies
        # Note: We could skip registration if strategy hasn't changed
        # but for demonstration, we always update it
        task_fe >> task_register >> task_signals

    # Deploy DAG
    print("Deploying DAG to Snowflake...")
    schema_obj = root.databases[db_name].schemas[schema_name]
    dag_op = DAGOperation(schema_obj)
    
    dag_op.deploy(dag, mode="or_replace")
    print("DAG deployed successfully.")

    # Handle environment-specific behavior
    if env_name == 'PRD':
        print("Environment is PRD: Resuming DAG schedule (hourly).")
        deployed_dag = dag_op.get(dag_name)
        deployed_dag.resume()
    else:
        print(f"Environment is {env_name}: Leaving DAG suspended.")
        print("Triggering manual run for testing...")
        deployed_dag = dag_op.get(dag_name)
        deployed_dag.execute()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_pipeline.py <ENV_NAME>")
        print("Example: python deploy_pipeline.py DEV")
        sys.exit(1)
    
    target_env = sys.argv[1]
    deploy(target_env)

