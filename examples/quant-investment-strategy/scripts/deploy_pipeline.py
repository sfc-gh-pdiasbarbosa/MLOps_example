"""
Investment Strategy Pipeline Deployment Script (Non-ML Example)

This script deploys the quantitative investment strategy pipeline to Snowflake.
It demonstrates that Snowflake's ML platform features (DAGs, Model Registry, 
Feature Store) work equally well with non-ML mathematical models.

Supports two execution modes:
- sprocs: Run tasks as Stored Procedures on Warehouses (default)
- mljobs: Run tasks as ML Jobs on Compute Pools

Pipeline Tasks:
1. Feature Engineering - Calculate technical indicators
2. Strategy Registration - Register the custom model
3. Signal Generation - Generate trading signals

Usage:
    python deploy_pipeline.py <ENV_NAME> [--mode sprocs|mljobs]
    
Example:
    python deploy_pipeline.py DEV
    python deploy_pipeline.py DEV --mode mljobs
"""

import os
import yaml
import sys
import argparse
from snowflake.snowpark import Session
from snowflake.core import Root
from snowflake.core.task.dagv1 import DAGOperation, DAG, DAGTask
from snowflake.core.task import Cron

# Add src to path
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


def get_mljob_submitter(file_path: str, compute_pool: str, stage: str, packages: list):
    """
    Returns a function that submits an ML Job when called.
    ML Jobs run on Compute Pools (container-based) instead of Warehouses.
    """
    from snowflake.ml.jobs import remote
    import importlib.util
    
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Could not find module at {file_path}")
    
    task_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = task_module
    spec.loader.exec_module(task_module)
    
    if not hasattr(task_module, 'main') or not callable(task_module.main):
        raise AttributeError(f"Module {file_path} must have a callable 'main' function for ML Jobs mode.")
    
    main_function = task_module.main
    
    def sp_submit_remote_job(session: Session) -> str:
        decorated_fn = remote(
            compute_pool=compute_pool,
            stage_name=stage,
            pip_requirements=packages,
        )(main_function)
        return decorated_fn(session)
    
    return sp_submit_remote_job


def deploy(env_name: str, execution_mode: str = "sprocs"):
    """
    Deploy the investment strategy pipeline DAG to the specified environment.
    
    This pipeline differs from ML pipelines:
    - No "training" task (strategy is rule-based, not learned)
    - Strategy registration is more like "publishing" than "training"
    - More frequent refresh for real-time trading scenarios
    
    Args:
        env_name: Target environment (DEV, SIT, UAT, PRD)
        execution_mode: 'sprocs' for Stored Procedures or 'mljobs' for ML Jobs
    """
    print(f"--- Deploying Investment Strategy Pipeline to Environment: {env_name} ---")
    print(f"Execution mode: {execution_mode.upper()}")
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'environments.yml')
    with open(config_path, "r") as f:
        full_config = yaml.safe_load(f)
    
    env_config = full_config[env_name].copy()
    env_config.update(full_config['default']) 
    
    session = get_snowpark_session()
    api_root = Root(session)
    
    db_name = env_config['database']
    schema_name = env_config['schema']
    wh_name = env_config['warehouse']
    
    # Stage locations
    code_stage = f"@{db_name}.{schema_name}.STRATEGY_CODE_STAGE"
    
    print(f"Target: {db_name}.{schema_name}")
    print(f"Warehouse: {wh_name}")
    
    # Define tasks configuration
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    strategy_logic_path = os.path.join(src_dir, 'strategy_logic.py')
    
    tasks_config = [
        {
            "name": "TASK_CALCULATE_INDICATORS",
            "file": strategy_logic_path,
            "func_name": "feature_engineering_main",
            "packages": ["snowflake-snowpark-python", "pandas", "numpy", "snowflake-ml-python"]
        },
        {
            "name": "TASK_REGISTER_STRATEGY",
            "file": strategy_logic_path,
            "func_name": "strategy_registration_main",
            "packages": ["snowflake-snowpark-python", "pandas", "numpy", "snowflake-ml-python"]
        },
        {
            "name": "TASK_GENERATE_SIGNALS",
            "file": strategy_logic_path,
            "func_name": "signal_generation_main",
            "packages": ["snowflake-snowpark-python", "pandas", "numpy", "snowflake-ml-python"]
        }
    ]
    
    # Common imports for all tasks
    imports = [strategy_logic_path]
    
    # Register stored procedures if using sprocs mode
    if execution_mode == "sprocs":
        print("\nRegistering stored procedures...")
        for task in tasks_config:
            session.sproc.register_from_file(
                file_path=task["file"],
                func_name=task["func_name"],
                name=f"{db_name}.{schema_name}.SP_{task['name']}",
                is_permanent=True,
                stage_location=code_stage,
                packages=task["packages"],
                replace=True,
                execute_as="caller",
                imports=imports
            )
            print(f"  ✅ Registered: SP_{task['name']}")
    
    # Build and deploy DAG
    print("\nBuilding DAG...")
    schema_obj = api_root.databases[db_name].schemas[schema_name]
    dag_op = DAGOperation(schema_obj)
    
    dag_name = "INVESTMENT_STRATEGY_PIPELINE"
    
    with DAG(
        dag_name,
        stage_location=code_stage,
        schedule=Cron("0 * * * *", "UTC"),  # Hourly for trading strategies
        warehouse=wh_name,
        packages=["snowflake-snowpark-python", "pandas", "numpy", "snowflake-ml-python"]
    ) as dag:
        dag_tasks = []
        
        for task in tasks_config:
            if execution_mode == "mljobs":
                # ML Jobs mode: submit to compute pool
                print(f"  Configuring ML Job for: {task['name']}")
                definition = get_mljob_submitter(
                    file_path=task["file"],
                    compute_pool=env_config.get('compute_pool', 'STRATEGY_COMPUTE_POOL'),
                    stage=code_stage,
                    packages=task["packages"]
                )
            else:
                # Stored Procedures mode: call the registered sproc
                print(f"  Configuring stored procedure call for: {task['name']}")
                definition = f"CALL {db_name}.{schema_name}.SP_{task['name']}()"
            
            dag_task = DAGTask(
                task["name"],
                definition=definition,
                warehouse=wh_name
            )
            dag_tasks.append(dag_task)
        
        # Chain tasks: Indicators >> Strategy >> Signals
        for i in range(len(dag_tasks) - 1):
            dag_tasks[i] >> dag_tasks[i + 1]
    
    # Deploy the DAG
    print("\nDeploying DAG to Snowflake...")
    dag_op.deploy(dag, mode="orreplace")
    print(f"✅ DAG '{dag_name}' deployed successfully")
    
    # Handle environment-specific behavior
    if env_name == 'PRD':
        print("Environment is PRD: Resuming DAG schedule (hourly)...")
        session.sql(f"ALTER TASK {db_name}.{schema_name}.{dag_name}$TASK_CALCULATE_INDICATORS RESUME").collect()
        print("✅ DAG schedule resumed")
    else:
        print(f"Environment is {env_name}: DAG created but suspended.")
        print(f"To run manually: EXECUTE TASK {db_name}.{schema_name}.{dag_name}$TASK_CALCULATE_INDICATORS;")
    
    print("\n✅ Investment Strategy Pipeline deployment complete!")
    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy Investment Strategy Pipeline to Snowflake")
    parser.add_argument("env", help="Target environment (DEV, SIT, UAT, PRD)")
    parser.add_argument("--mode", choices=["sprocs", "mljobs"], default="sprocs",
                        help="Execution mode: 'sprocs' for Stored Procedures (default) or 'mljobs' for ML Jobs")
    
    args = parser.parse_args()
    deploy(args.env, args.mode)
