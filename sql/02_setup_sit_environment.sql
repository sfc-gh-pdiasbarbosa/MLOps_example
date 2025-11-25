-- ============================================================================
-- SIT Environment Setup for ML Pipeline
-- ============================================================================
-- Description: Creates all Snowflake objects for System Integration Test environment
-- Execute as: ACCOUNTADMIN or role with appropriate privileges
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE SIT_WH_S;

-- ============================================================================
-- 1. RAW DATA DATABASE & OBJECTS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS SIT_RAW_DB
    COMMENT = 'SIT - Raw data source database';

USE DATABASE SIT_RAW_DB;

CREATE SCHEMA IF NOT EXISTS PUBLIC
    COMMENT = 'Raw data schema for SIT';

-- Sample raw data table (customers)
CREATE OR REPLACE TABLE SIT_RAW_DB.PUBLIC.CUSTOMERS (
    CUSTOMER_ID VARCHAR(50) PRIMARY KEY,
    CUSTOMER_NAME VARCHAR(200),
    AGE INTEGER,
    ACCOUNT_BALANCE DECIMAL(18,2),
    TENURE_MONTHS INTEGER,
    NUM_PRODUCTS INTEGER,
    HAS_CREDIT_CARD BOOLEAN,
    IS_ACTIVE_MEMBER BOOLEAN,
    TARGET_LABEL INTEGER,  -- 1 = churned, 0 = retained
    LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'SIT: Raw customer data for churn prediction';

-- ============================================================================
-- 2. ML WORKLOAD DATABASE & SCHEMAS
-- ============================================================================

CREATE DATABASE IF NOT EXISTS SIT_ML_DB
    COMMENT = 'SIT - ML pipeline database';

USE DATABASE SIT_ML_DB;

-- Schema for DAG Tasks and Stored Procedures
CREATE SCHEMA IF NOT EXISTS PIPELINES
    COMMENT = 'SIT: Contains ML pipeline tasks and DAG definitions';

-- Schema for Feature Store
CREATE SCHEMA IF NOT EXISTS FEATURES
    COMMENT = 'SIT: Feature Store objects and feature views';

-- Schema for Model Outputs
CREATE SCHEMA IF NOT EXISTS OUTPUT
    COMMENT = 'SIT: ML inference outputs and predictions';

-- ============================================================================
-- 3. STAGES
-- ============================================================================

USE SCHEMA SIT_ML_DB.PIPELINES;

-- Stage for Python code artifacts
CREATE STAGE IF NOT EXISTS ML_CODE_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'SIT: Storage for Python ML logic files';

-- Stage for model artifacts
CREATE STAGE IF NOT EXISTS MODELS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'SIT: Storage for trained ML models';

-- ============================================================================
-- 4. OUTPUT TABLES
-- ============================================================================

USE SCHEMA SIT_ML_DB.OUTPUT;

-- Predictions output table
CREATE TABLE IF NOT EXISTS PREDICTIONS (
    CUSTOMER_ID VARCHAR(50),
    PREDICTION INTEGER,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODEL_VERSION VARCHAR(50),
    CONFIDENCE_SCORE DECIMAL(5,4)
)
COMMENT = 'SIT: ML model prediction outputs';

-- ============================================================================
-- 5. SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample data into raw customers table
USE SCHEMA SIT_RAW_DB.PUBLIC;

INSERT INTO CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, AGE, ACCOUNT_BALANCE, TENURE_MONTHS, NUM_PRODUCTS, HAS_CREDIT_CARD, IS_ACTIVE_MEMBER, TARGET_LABEL)
SELECT 
    'CUST_' || SEQ4() AS CUSTOMER_ID,
    'Customer ' || SEQ4() AS CUSTOMER_NAME,
    UNIFORM(18, 75, RANDOM()) AS AGE,
    UNIFORM(0, 100000, RANDOM()) AS ACCOUNT_BALANCE,
    UNIFORM(0, 120, RANDOM()) AS TENURE_MONTHS,
    UNIFORM(1, 4, RANDOM()) AS NUM_PRODUCTS,
    CASE WHEN UNIFORM(0, 1, RANDOM()) = 1 THEN TRUE ELSE FALSE END AS HAS_CREDIT_CARD,
    CASE WHEN UNIFORM(0, 1, RANDOM()) = 1 THEN TRUE ELSE FALSE END AS IS_ACTIVE_MEMBER,
    CASE WHEN UNIFORM(0, 10, RANDOM()) > 8 THEN 1 ELSE 0 END AS TARGET_LABEL
FROM TABLE(GENERATOR(ROWCOUNT => 5000));

-- ============================================================================
-- 6. VERIFY SETUP
-- ============================================================================

SHOW DATABASES LIKE 'SIT%';
SHOW SCHEMAS IN DATABASE SIT_ML_DB;
SHOW STAGES IN SCHEMA SIT_ML_DB.PIPELINES;
SHOW TABLES IN SCHEMA SIT_ML_DB.OUTPUT;

SELECT 'SIT Environment Setup Complete!' AS STATUS,
       COUNT(*) AS SAMPLE_RECORDS 
FROM SIT_RAW_DB.PUBLIC.CUSTOMERS;

