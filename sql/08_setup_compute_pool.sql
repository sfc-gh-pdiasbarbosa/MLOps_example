-- ============================================================================
-- Compute Pool Setup for Container Runtime and ML Jobs
-- ============================================================================
-- Description: Creates compute pools for:
--   - ML Jobs (remote execution of training/inference workloads)
--   - Container Runtime (Snowflake Notebooks with GPU/CPU)
--   - Model Serving (SPCS-based REST API endpoints)
--   - Distributed Training (multi-node XGBoost, LightGBM, PyTorch)
-- Execute as: ACCOUNTADMIN
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- ============================================================================
-- 1. CPU COMPUTE POOL (for general ML workloads)
-- ============================================================================
-- Used for: ML Jobs, batch training, hyperparameter tuning
-- Instance family: CPU_X64_S provides a good balance of CPU and memory.

CREATE COMPUTE POOL IF NOT EXISTS ML_CPU_POOL
    MIN_NODES = 1
    MAX_NODES = 3
    INSTANCE_FAMILY = CPU_X64_S
    AUTO_RESUME = TRUE
    AUTO_SUSPEND_SECS = 300
    COMMENT = 'CPU compute pool for ML training and inference workloads';

-- ============================================================================
-- 2. GPU COMPUTE POOL (for deep learning and large-scale training)
-- ============================================================================
-- Used for: PyTorch distributed training, GPU-accelerated XGBoost/LightGBM
-- Instance family: GPU_NV_S provides NVIDIA GPUs for training.
--
-- NOTE: GPU instances have higher cost. Adjust MAX_NODES and
-- AUTO_SUSPEND_SECS based on your usage patterns.

CREATE COMPUTE POOL IF NOT EXISTS ML_GPU_POOL
    MIN_NODES = 1
    MAX_NODES = 2
    INSTANCE_FAMILY = GPU_NV_S
    AUTO_RESUME = TRUE
    AUTO_SUSPEND_SECS = 120
    COMMENT = 'GPU compute pool for deep learning and distributed training';

-- ============================================================================
-- 3. MODEL SERVING POOL (for real-time inference endpoints)
-- ============================================================================
-- Used for: SPCS model serving (REST API endpoints)
-- Instance family: CPU_X64_XS is cost-effective for inference.
-- Kept always available (low MIN_NODES) for low-latency serving.

CREATE COMPUTE POOL IF NOT EXISTS ML_SERVING_POOL
    MIN_NODES = 1
    MAX_NODES = 2
    INSTANCE_FAMILY = CPU_X64_XS
    AUTO_RESUME = TRUE
    AUTO_SUSPEND_SECS = 600
    COMMENT = 'Compute pool for model serving via SPCS REST endpoints';

-- ============================================================================
-- 4. GRANTS
-- ============================================================================
-- Grant USAGE on compute pools to ML roles.

-- DEV
GRANT USAGE ON COMPUTE POOL ML_CPU_POOL TO ROLE ML_DEV_ROLE;
GRANT USAGE ON COMPUTE POOL ML_GPU_POOL TO ROLE ML_DEV_ROLE;
GRANT USAGE ON COMPUTE POOL ML_SERVING_POOL TO ROLE ML_DEV_ROLE;
GRANT MONITOR ON COMPUTE POOL ML_CPU_POOL TO ROLE ML_DEV_ROLE;
GRANT MONITOR ON COMPUTE POOL ML_GPU_POOL TO ROLE ML_DEV_ROLE;

-- PRD
GRANT USAGE ON COMPUTE POOL ML_CPU_POOL TO ROLE ML_PRD_ROLE;
GRANT USAGE ON COMPUTE POOL ML_SERVING_POOL TO ROLE ML_PRD_ROLE;
GRANT MONITOR ON COMPUTE POOL ML_CPU_POOL TO ROLE ML_PRD_ROLE;

-- CI/CD
GRANT USAGE ON COMPUTE POOL ML_CPU_POOL TO ROLE ML_CICD_ROLE;
GRANT USAGE ON COMPUTE POOL ML_GPU_POOL TO ROLE ML_CICD_ROLE;
GRANT USAGE ON COMPUTE POOL ML_SERVING_POOL TO ROLE ML_CICD_ROLE;

-- ============================================================================
-- 5. VERIFY
-- ============================================================================

SHOW COMPUTE POOLS;

SELECT 'Compute pool setup complete.' AS STATUS;
