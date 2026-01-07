"""
ML Pipeline Deployment Script for Customer Churn Prediction

This script deploys the ML retraining pipeline to Snowflake as a DAG.
It supports two execution modes:
- sprocs: Run tasks as Stored Procedures on Warehouses (default, lighter workloads)
- mljobs: Run tasks as ML Jobs on Compute Pools (heavier ML training)

Pipeline Tasks:
1. Feature Engineering - Updates Feature Store
2. Model Training - Retrains and registers model
3. Batch Inference - Runs predictions

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
    Handles PEM-encoded private keys from environment variables.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    # Load and parse the private key from PEM format
    private_key_pem = os.environ["SNOWFLAKE_PRIVATE_KEY"]
    
    # Handle potential escaped newlines from GitHub secrets
    if "\\n" in private_key_pem:
        private_key_pem = private_key_pem.replace("\\n", "\n")
    
    # Parse the PEM key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend()
    )
    
    # Convert to DER format (bytes) which Snowflake expects
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    connection_params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "private_key": private_key_bytes,
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
    Deploy the ML pipeline DAG to the specified environment.
    
    Args:
        env_name: Target environment (DEV, SIT, UAT, PRD)
        execution_mode: 'sprocs' for Stored Procedures or 'mljobs' for ML Jobs
    """
    print(f"--- Deploying ML Pipeline to Environment: {env_name} ---")
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
    code_stage = f"@{db_name}.{schema_name}.ML_CODE_STAGE"
    
    print(f"Target: {db_name}.{schema_name}")
    print(f"Warehouse: {wh_name}")
    
    # Define tasks configuration
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    ml_logic_path = os.path.join(src_dir, 'ml_logic.py')
    
    tasks_config = [
        {
            "name": "TASK_FEATURE_ENGINEERING",
            "file": ml_logic_path,
            "func_name": "feature_engineering_main",
            "packages": ["snowflake-snowpark-python", "pandas", "snowflake-ml-python"]
        },
        {
            "name": "TASK_MODEL_TRAINING",
            "file": ml_logic_path,
            "func_name": "model_training_main",
            "packages": ["snowflake-snowpark-python", "pandas", "scikit-learn", "snowflake-ml-python"]
        },
        {
            "name": "TASK_INFERENCE",
            "file": ml_logic_path,
            "func_name": "inference_main",
            "packages": ["snowflake-snowpark-python", "pandas", "snowflake-ml-python"]
        }
    ]
    
    # Common imports for all tasks
    imports = [ml_logic_path]
    
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
    
    dag_name = "ML_RETRAINING_PIPELINE"
    
    with DAG(
        dag_name,
        stage_location=code_stage,
        schedule=Cron("0 2 * * *", "UTC"),  # Daily at 2 AM UTC
        warehouse=wh_name,
        packages=["snowflake-snowpark-python", "pandas", "snowflake-ml-python"]
    ) as dag:
        dag_tasks = []
        
        for task in tasks_config:
            if execution_mode == "mljobs":
                # ML Jobs mode: submit to compute pool
                print(f"  Configuring ML Job for: {task['name']}")
                definition = get_mljob_submitter(
                    file_path=task["file"],
                    compute_pool=env_config.get('compute_pool', 'ML_COMPUTE_POOL'),
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
        
        # Chain tasks: FE >> Training >> Inference
        for i in range(len(dag_tasks) - 1):
            dag_tasks[i] >> dag_tasks[i + 1]
    
    # Deploy the DAG
    print("\nDeploying DAG to Snowflake...")
    dag_op.deploy(dag, mode="orreplace")
    print(f"✅ DAG '{dag_name}' deployed successfully")
    
    # Handle environment-specific behavior
    if env_name == 'PRD':
        print("Environment is PRD: Resuming DAG schedule...")
        # Note: In production, you'd resume the root task
        session.sql(f"ALTER TASK {db_name}.{schema_name}.{dag_name}$TASK_FEATURE_ENGINEERING RESUME").collect()
        print("✅ DAG schedule resumed")
    else:
        print(f"Environment is {env_name}: DAG created but suspended.")
        print(f"To run manually: EXECUTE TASK {db_name}.{schema_name}.{dag_name}$TASK_FEATURE_ENGINEERING;")
    
    print("\n✅ ML Pipeline deployment complete!")
    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ML Pipeline to Snowflake")
    parser.add_argument("env", help="Target environment (DEV, SIT, UAT, PRD)")
    parser.add_argument("--mode", choices=["sprocs", "mljobs"], default="sprocs",
                        help="Execution mode: 'sprocs' for Stored Procedures (default) or 'mljobs' for ML Jobs")
    
    args = parser.parse_args()
    deploy(args.env, args.mode)
