import os
import yaml
import sys
from datetime import timedelta
from snowflake.snowpark import Session
from snowflake.core import Root
from snowflake.core.task.dag import DAG, DAGTask, DAGOperation
from snowflake.core.task.context import StoredProcedureCall

# Add src to path to import logic definitions
sys.path.append('src')
import ml_logic

def get_snowpark_session():
    """
    Creates a session using Key Pair authentication.
    Using raw content from env var.
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

def deploy(env_name):
    print(f"--- Deploying to Environment: {env_name} ---")
    
    with open("config/environments.yaml", "r") as f:
        full_config = yaml.safe_load(f)
    
    env_config = full_config[env_name]
    env_config.update(full_config['default']) 
    
    session = get_snowpark_session()
    root = Root(session)
    
    schema_name = env_config['schema']
    db_name = env_config['database']
    wh_name = env_config['warehouse']
    
    # Locations
    code_stage = f"@{db_name}.{schema_name}.ML_CODE_STAGE"
    model_stage = f"@{db_name}.{schema_name}.MODELS_STAGE"

    dag_name = "ML_RETRAINING_PIPELINE"
    
    print("Defining DAG structure...")
    
    with DAG(dag_name, schedule=timedelta(hours=24), warehouse=wh_name) as dag:
        
        # --- Task 1: Feature Engineering (Feature Store) ---
        task_fe = DAGTask(
            "TASK_FEATURE_ENG",
            StoredProcedureCall(
                ml_logic.feature_engineering_task,
                args=[
                    env_config['tables']['raw_data'],
                    env_config['tables']['feature_store'] # Passed as the Feature View name
                ],
                stage_location=code_stage,
                packages=["snowflake-snowpark-python", "pandas", "snowflake-ml-python"],
                imports=[f"{code_stage}/ml_logic.py"]
            ),
            warehouse=wh_name
        )

        # --- Task 2: Training ---
        task_train = DAGTask(
            "TASK_TRAINING",
            StoredProcedureCall(
                ml_logic.model_training_task,
                args=[
                    env_config['tables']['feature_store'], # Reads the Feature View (Table)
                    env_config['model_name'],
                    model_stage
                ],
                stage_location=code_stage,
                packages=["snowflake-snowpark-python", "pandas", "scikit-learn", "snowflake-ml-python"],
                imports=[f"{code_stage}/ml_logic.py"]
            ),
            warehouse=wh_name
        )

        # --- Task 3: Inference ---
        task_infer = DAGTask(
            "TASK_INFERENCE",
            StoredProcedureCall(
                ml_logic.inference_task,
                args=[
                    env_config['tables']['feature_store'],
                    env_config['model_name'],
                    env_config['tables']['inference_output']
                ],
                stage_location=code_stage,
                packages=["snowflake-snowpark-python", "pandas", "snowflake-ml-python"],
                imports=[f"{code_stage}/ml_logic.py"]
            ),
            warehouse=wh_name
        )

        # Dependencies
        task_fe >> task_train >> task_infer

    # Deploy
    print("Deploying DAG to Snowflake...")
    schema_obj = root.databases[db_name].schemas[schema_name]
    dag_op = DAGOperation(schema_obj)
    
    dag_op.deploy(dag, mode="or_replace")
    print("DAG deployed successfully.")

    if env_name == 'PRD':
        print("Environment is PRD: Resuming DAG schedule.")
        deployed_dag = dag_op.get(dag_name)
        deployed_dag.resume()
    else:
        print(f"Environment is {env_name}: Leaving DAG suspended.")
        print("Triggering manual run...")
        deployed_dag = dag_op.get(dag_name)
        deployed_dag.execute()

if __name__ == "__main__":
    target_env = sys.argv[1]
    deploy(target_env)