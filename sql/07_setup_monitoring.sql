-- ============================================================================
-- Monitoring and ML Observability Setup
-- ============================================================================
-- Description: Creates objects and grants required for ML Observability
--              (Model Monitors, drift detection, performance tracking)
-- Execute as:  ACCOUNTADMIN
-- Prerequisite: Run 01-04 scripts first to create databases, schemas, roles
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- ============================================================================
-- 1. MONITORING SCHEMA (per environment)
-- ============================================================================
-- Model Monitor objects, baseline tables, and monitoring source tables
-- live in a dedicated MONITORING schema.

CREATE SCHEMA IF NOT EXISTS DEV_ML_DB.MONITORING
    COMMENT = 'DEV: ML Observability - model monitors, baselines, drift tracking';

CREATE SCHEMA IF NOT EXISTS SIT_ML_DB.MONITORING
    COMMENT = 'SIT: ML Observability - model monitors, baselines, drift tracking';

CREATE SCHEMA IF NOT EXISTS UAT_ML_DB.MONITORING
    COMMENT = 'UAT: ML Observability - model monitors, baselines, drift tracking';

CREATE SCHEMA IF NOT EXISTS PRD_ML_DB.MONITORING
    COMMENT = 'PRD: ML Observability - model monitors, baselines, drift tracking';

-- ============================================================================
-- 2. GRANTS FOR MODEL MONITOR CREATION
-- ============================================================================
-- CREATE MODEL MONITOR requires specific privileges on the schema
-- and USAGE on the warehouse used for monitor refresh.

-- DEV
GRANT ALL ON SCHEMA DEV_ML_DB.MONITORING TO ROLE ML_DEV_ROLE;
GRANT CREATE TABLE ON SCHEMA DEV_ML_DB.MONITORING TO ROLE ML_DEV_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA DEV_ML_DB.MONITORING TO ROLE ML_DEV_ROLE;

-- SIT
GRANT ALL ON SCHEMA SIT_ML_DB.MONITORING TO ROLE ML_SIT_ROLE;
GRANT CREATE TABLE ON SCHEMA SIT_ML_DB.MONITORING TO ROLE ML_SIT_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA SIT_ML_DB.MONITORING TO ROLE ML_SIT_ROLE;

-- UAT
GRANT ALL ON SCHEMA UAT_ML_DB.MONITORING TO ROLE ML_UAT_ROLE;
GRANT CREATE TABLE ON SCHEMA UAT_ML_DB.MONITORING TO ROLE ML_UAT_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA UAT_ML_DB.MONITORING TO ROLE ML_UAT_ROLE;

-- PRD
GRANT ALL ON SCHEMA PRD_ML_DB.MONITORING TO ROLE ML_PRD_ROLE;
GRANT CREATE TABLE ON SCHEMA PRD_ML_DB.MONITORING TO ROLE ML_PRD_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA PRD_ML_DB.MONITORING TO ROLE ML_PRD_ROLE;

-- CI/CD role
GRANT ALL ON SCHEMA DEV_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON SCHEMA SIT_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON SCHEMA UAT_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON SCHEMA PRD_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA DEV_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA SIT_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA UAT_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA PRD_ML_DB.MONITORING TO ROLE ML_CICD_ROLE;

-- ============================================================================
-- 3. VIEW LINEAGE PRIVILEGE
-- ============================================================================
-- Required for ML Lineage exploration via Python APIs and SnowSight UI.

GRANT VIEW LINEAGE ON ACCOUNT TO ROLE ML_DEV_ROLE;
GRANT VIEW LINEAGE ON ACCOUNT TO ROLE ML_SIT_ROLE;
GRANT VIEW LINEAGE ON ACCOUNT TO ROLE ML_UAT_ROLE;
GRANT VIEW LINEAGE ON ACCOUNT TO ROLE ML_PRD_ROLE;
GRANT VIEW LINEAGE ON ACCOUNT TO ROLE ML_CICD_ROLE;

-- ============================================================================
-- 4. VERIFY
-- ============================================================================

SHOW SCHEMAS LIKE 'MONITORING' IN DATABASE DEV_ML_DB;
SHOW SCHEMAS LIKE 'MONITORING' IN DATABASE PRD_ML_DB;

SELECT 'Monitoring setup complete.' AS STATUS;
