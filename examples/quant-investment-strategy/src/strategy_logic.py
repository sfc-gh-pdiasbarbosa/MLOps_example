"""
Investment Strategy Logic (Non-ML Custom Model Example)

This module demonstrates how to use Snowflake's ML platform features
(Feature Store, Model Registry, DAGs) with non-ML mathematical models.

Use Case: Quantitative Investment Strategy
- Calculate technical indicators (RSI, Moving Averages, MACD)
- Generate trading signals based on mathematical rules
- Track and version the strategy as a "custom model"

This pattern is common in:
- Quantitative finance
- Risk modeling
- Pricing engines
- Portfolio optimization
- Any rule-based decision system
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from snowflake.snowpark.session import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import FloatType, StringType
from snowflake.ml.registry import Registry
from snowflake.ml.model import custom_model
from snowflake.ml.feature_store import (
    FeatureStore,
    Entity,
    FeatureView,
    CreationMode
)

# Set up logging
logger = logging.getLogger("investment_strategy_pipeline")


# =============================================================================
# CUSTOM MODEL CLASS - This wraps our mathematical strategy for Model Registry
# =============================================================================

class MomentumStrategy(custom_model.CustomModel):
    """
    A quantitative momentum-based investment strategy.
    
    This is a NON-ML model that uses mathematical rules to generate
    trading signals. It demonstrates how to register ANY Python logic
    in Snowflake's Model Registry using the CustomModel base class.
    
    Strategy Logic:
    - Buy Signal: RSI < 30 (oversold) AND price > 20-day MA
    - Sell Signal: RSI > 70 (overbought) OR price < 20-day MA
    - Hold otherwise
    
    Parameters are versioned and tracked in the Model Registry.
    """
    
    def __init__(self, context: custom_model.ModelContext) -> None:
        """Initialize the strategy with configurable parameters."""
        super().__init__(context)
        
        # Strategy parameters (can be tuned and versioned)
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_short_window = 20
        self.ma_long_window = 50
        self.position_size_pct = 0.02  # 2% of portfolio per position
    
    @custom_model.inference_api
    def predict(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for each asset.
        
        This method is called by Model Registry's run() function.
        It applies the momentum strategy rules to generate signals.
        
        Args:
            input_df: DataFrame with columns:
                - ASSET_ID: Unique identifier
                - RSI_14: 14-day Relative Strength Index
                - MA_20: 20-day Moving Average
                - MA_50: 50-day Moving Average
                - CURRENT_PRICE: Latest price
                
        Returns:
            DataFrame with columns:
                - ASSET_ID: Asset identifier
                - SIGNAL: 'BUY', 'SELL', or 'HOLD'
                - SIGNAL_STRENGTH: Numeric strength (0-1)
                - POSITION_SIZE: Recommended position size
                - REASONING: Explanation of the signal
        """
        results = []
        
        for _, row in input_df.iterrows():
            asset_id = row['ASSET_ID']
            rsi = row['RSI_14']
            ma_short = row['MA_20']
            ma_long = row['MA_50']
            current_price = row['CURRENT_PRICE']
            
            # Apply strategy rules
            signal, strength, reasoning = self._evaluate_signal(
                rsi, ma_short, ma_long, current_price
            )
            
            # Calculate position size based on signal strength
            position_size = self.position_size_pct * strength if signal == 'BUY' else 0.0
            
            results.append({
                'ASSET_ID': asset_id,
                'SIGNAL': signal,
                'SIGNAL_STRENGTH': round(strength, 4),
                'POSITION_SIZE': round(position_size, 4),
                'REASONING': reasoning
            })
        
        return pd.DataFrame(results)
    
    def _evaluate_signal(
        self, 
        rsi: float, 
        ma_short: float, 
        ma_long: float, 
        current_price: float
    ) -> tuple:
        """
        Evaluate trading signal based on momentum rules.
        
        Returns:
            Tuple of (signal, strength, reasoning)
        """
        reasons = []
        buy_score = 0
        sell_score = 0
        
        # RSI Analysis
        if rsi < self.rsi_oversold:
            buy_score += 0.4
            reasons.append(f"RSI={rsi:.1f} (oversold)")
        elif rsi > self.rsi_overbought:
            sell_score += 0.4
            reasons.append(f"RSI={rsi:.1f} (overbought)")
        else:
            reasons.append(f"RSI={rsi:.1f} (neutral)")
        
        # Moving Average Analysis
        if current_price > ma_short > ma_long:
            buy_score += 0.3
            reasons.append("Price > MA20 > MA50 (bullish trend)")
        elif current_price < ma_short < ma_long:
            sell_score += 0.3
            reasons.append("Price < MA20 < MA50 (bearish trend)")
        elif current_price > ma_short:
            buy_score += 0.15
            reasons.append("Price > MA20 (short-term bullish)")
        else:
            sell_score += 0.15
            reasons.append("Price < MA20 (short-term bearish)")
        
        # MA Crossover
        if ma_short > ma_long:
            buy_score += 0.2
            reasons.append("Golden cross (MA20 > MA50)")
        else:
            sell_score += 0.2
            reasons.append("Death cross (MA20 < MA50)")
        
        # Determine signal
        if buy_score > sell_score and buy_score >= 0.5:
            return 'BUY', buy_score, "; ".join(reasons)
        elif sell_score > buy_score and sell_score >= 0.5:
            return 'SELL', sell_score, "; ".join(reasons)
        else:
            return 'HOLD', max(buy_score, sell_score), "; ".join(reasons)


# =============================================================================
# PIPELINE TASKS - Feature Engineering, Strategy Registration, Signal Generation
# =============================================================================

def feature_engineering_task(session: Session, source_table: str, target_fs_object: str) -> str:
    """
    Task 1: Calculate technical indicators and register as Feature View.
    
    This demonstrates using Feature Store for non-ML features:
    - RSI (Relative Strength Index)
    - Moving Averages (20-day, 50-day)
    - Price momentum indicators
    
    Args:
        session: Snowpark Session
        source_table: Input table with price data (ASSET_ID, DATE, CLOSE_PRICE)
        target_fs_object: Feature View name (e.g., DB.SCHEMA.ASSET_FEATURES)
    
    Returns:
        Success message
    """
    logger.info(f"Starting technical indicator calculation from {source_table}")
    
    # Parse target location - strip quotes from all values
    try:
        parts = target_fs_object.split('.')
        if len(parts) == 3:
            db_name, schema_name, fv_name = [p.strip('"') for p in parts]
        else:
            db_name = session.get_current_database().strip('"')
            schema_name = session.get_current_schema().strip('"')
            fv_name = target_fs_object.strip('"')
    except Exception:
        db_name = session.get_current_database().strip('"')
        schema_name = session.get_current_schema().strip('"')
        fv_name = target_fs_object.strip('"')
    
    warehouse = session.get_current_warehouse().strip('"')
    logger.info(f"Using database={db_name}, schema={schema_name}, warehouse={warehouse}")
    
    # Initialize Feature Store
    # Use CREATE_IF_NOT_EXIST to create Feature Store metadata if not present
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=warehouse,
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )
    
    # Define Entity (ASSET_ID is the primary key)
    entity_name = "ASSET_ENTITY"
    asset_entity = Entity(
        name=entity_name,
        join_keys=["ASSET_ID"],
        desc="Unique Asset/Security Identifier"
    )
    fs.register_entity(asset_entity)
    logger.info(f"Entity {entity_name} registered.")
    
    # Read raw price data
    logger.info(f"Reading source table: {source_table}")
    df_raw = session.table(source_table)
    
    # Log available columns for debugging
    logger.info(f"Source table columns: {df_raw.columns}")
    
    # Build feature DataFrame - only select columns that exist
    # Use uppercase column names (Snowflake default)
    available_cols = [c.upper() for c in df_raw.columns]
    
    # Start with required columns
    select_cols = [
        F.col("ASSET_ID"),
        F.col("DATE"),
        F.col("CLOSE_PRICE").alias("CURRENT_PRICE")
    ]
    
    # Add optional columns with defaults if they don't exist
    if "RSI_14" in available_cols:
        select_cols.append(F.coalesce(F.col("RSI_14"), F.lit(50.0)).alias("RSI_14"))
    else:
        select_cols.append(F.lit(50.0).alias("RSI_14"))
        
    if "MA_20" in available_cols:
        select_cols.append(F.coalesce(F.col("MA_20"), F.col("CLOSE_PRICE")).alias("MA_20"))
    else:
        select_cols.append(F.col("CLOSE_PRICE").alias("MA_20"))
        
    if "MA_50" in available_cols:
        select_cols.append(F.coalesce(F.col("MA_50"), F.col("CLOSE_PRICE")).alias("MA_50"))
    else:
        select_cols.append(F.col("CLOSE_PRICE").alias("MA_50"))
        
    if "VOLUME" in available_cols:
        select_cols.append(F.coalesce(F.col("VOLUME"), F.lit(0)).alias("VOLUME"))
    else:
        select_cols.append(F.lit(0).alias("VOLUME"))
        
    if "VOLATILITY_20" in available_cols:
        select_cols.append(F.coalesce(F.col("VOLATILITY_20"), F.lit(0.0)).alias("VOLATILITY_20"))
    else:
        select_cols.append(F.lit(0.0).alias("VOLATILITY_20"))
    
    df_features = df_raw.select(*select_cols)
    
    # Create Feature View
    fv = FeatureView(
        name=fv_name,
        entities=[asset_entity],
        feature_df=df_features,
        refresh_freq="1 hour",  # More frequent for trading strategies
        desc="Technical indicators for investment strategy"
    )
    
    # Register Feature View
    fs.register_feature_view(
        feature_view=fv,
        version="v1",
        overwrite=True
    )
    
    return f"Success: Feature View {fv_name} (v1) with technical indicators registered"


def strategy_registration_task(session: Session, feature_view_path: str, model_name: str, stage_location: str) -> str:
    """
    Task 2: Register the investment strategy as a Custom Model.
    
    This demonstrates registering a NON-ML model in the Model Registry.
    Key differences from ML models:
    - Uses CustomModel base class instead of sklearn/pytorch
    - Parameters are embedded in the model class
    - Logic is deterministic (no training phase)
    
    Args:
        session: Snowpark Session
        feature_view_path: Path to feature data (DB.SCHEMA.FV_NAME format)
        model_name: Name for the strategy in registry
        stage_location: Stage for model artifacts
    
    Returns:
        Success message
    """
    logger.info(f"Registering investment strategy as custom model: {model_name}")
    
    # Parse feature view path
    parts = feature_view_path.split('.')
    if len(parts) == 3:
        db_name, schema_name, fv_name = [p.strip('"') for p in parts]
    else:
        db_name = session.get_current_database().strip('"')
        schema_name = "FEATURES"
        fv_name = feature_view_path.strip('"')
    
    warehouse = session.get_current_warehouse().strip('"')
    
    # Get sample data from Feature Store
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=warehouse,
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )
    
    # Get feature view and sample data
    fv = fs.get_feature_view(name=fv_name, version="v1")
    df_sample = fv.feature_df.limit(10)
    sample_pdf = df_sample.to_pandas()
    
    # Ensure required columns exist
    required_cols = ['ASSET_ID', 'RSI_14', 'MA_20', 'MA_50', 'CURRENT_PRICE']
    for col in required_cols:
        if col not in sample_pdf.columns:
            raise ValueError(f"Required column {col} missing from feature data")
    
    # Create model context (can include configuration parameters)
    model_context = custom_model.ModelContext()
    
    # Instantiate our custom strategy model
    strategy = MomentumStrategy(model_context)
    
    # Register in Model Registry
    reg = Registry(session=session)
    
    # Generate timestamp-based version name to avoid conflicts
    from datetime import datetime
    version_name = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Log the custom model
    mv = reg.log_model(
        model=strategy,
        model_name=model_name,
        version_name=version_name,
        conda_dependencies=["pandas", "numpy"],
        comment=f"Momentum-based investment strategy at {datetime.utcnow().isoformat()}",
        sample_input_data=sample_pdf[required_cols].head()
    )
    
    logger.info(f"Strategy {model_name} version {version_name} registered successfully")
    
    return f"Success: Strategy {model_name} version {version_name} registered"


def signal_generation_task(session: Session, feature_table: str, model_name: str, output_table: str) -> str:
    """
    Task 3: Generate trading signals using the registered strategy.
    
    This is analogous to "inference" in ML pipelines, but for our
    deterministic rule-based strategy.
    
    Args:
        session: Snowpark Session
        feature_table: Path to Feature View (DB.SCHEMA.FV_NAME format)
        model_name: Name of the strategy in registry
        output_table: Output table for trading signals
    
    Returns:
        Success message
    """
    logger.info(f"Generating trading signals using strategy {model_name}")
    
    # Parse feature view path
    parts = feature_table.split('.')
    if len(parts) == 3:
        db_name, schema_name, fv_name = [p.strip('"') for p in parts]
    else:
        db_name = session.get_current_database().strip('"')
        schema_name = "FEATURES"
        fv_name = feature_table.strip('"')
    
    warehouse = session.get_current_warehouse().strip('"')
    
    # Get features from Feature Store
    fs = FeatureStore(
        session=session,
        database=db_name,
        name=schema_name,
        default_warehouse=warehouse,
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST
    )
    
    fv = fs.get_feature_view(name=fv_name, version="v1")
    df_features = fv.feature_df
    
    # Load strategy from registry
    reg = Registry(session=session)
    model = reg.get_model(model_name)
    
    # Get latest version
    versions = model.versions()
    if not versions:
        raise ValueError(f"No versions found for strategy {model_name}")
    strategy_ref = versions[0]
    logger.info(f"Using strategy version: {strategy_ref.version_name}")
    
    # Run the strategy (this calls the predict method of our CustomModel)
    signals_df = strategy_ref.run(df_features, function_name="predict")
    
    # Add metadata
    signals_df = signals_df.with_column("SIGNAL_TIMESTAMP", F.current_timestamp())
    signals_df = signals_df.with_column("STRATEGY_VERSION", F.lit(strategy_ref.version_name))
    
    # Save signals
    signals_df.write.mode("overwrite").save_as_table(output_table)
    
    # Log summary
    signal_counts = signals_df.group_by("SIGNAL").count().collect()
    logger.info(f"Signal generation complete: {signal_counts}")
    
    return f"Success: Trading signals saved to {output_table}"


# =============================================================================
# UTILITY FUNCTIONS - Technical Indicator Calculations
# =============================================================================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
    
    Returns:
        Series of RSI values
    """
    delta = prices.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_moving_averages(prices: pd.Series, windows: List[int] = [20, 50]) -> Dict[str, pd.Series]:
    """
    Calculate moving averages for given windows.
    
    Args:
        prices: Series of closing prices
        windows: List of window sizes
    
    Returns:
        Dictionary of MA series
    """
    result = {}
    for window in windows:
        result[f'MA_{window}'] = prices.rolling(window=window, min_periods=window).mean()
    return result


def calculate_volatility(prices: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate rolling volatility (standard deviation of returns).
    
    Args:
        prices: Series of closing prices
        window: Rolling window size
    
    Returns:
        Series of volatility values
    """
    returns = prices.pct_change()
    volatility = returns.rolling(window=window, min_periods=window).std() * np.sqrt(252)  # Annualized
    return volatility


# =============================================================================
# MAIN ENTRY POINTS - For Stored Procedures / ML Jobs
# =============================================================================
# These functions are called by DAG tasks. They read configuration from
# session context and invoke the actual task logic.

def main(session: Session) -> str:
    """
    Default main function - runs the full pipeline sequentially.
    Useful for ML Jobs mode where a single job runs everything.
    """
    db = session.get_current_database().strip('"')
    schema = session.get_current_schema().strip('"')
    
    # Derive environment prefix from database name (e.g., DEV_ML_DB -> DEV)
    env_prefix = db.split("_")[0]
    
    # Configuration
    # Source table is in RAW_DB, features are in ML_DB
    source_table = f"{env_prefix}_RAW_DB.PUBLIC.MARKET_DATA"
    feature_view = f"{db}.FEATURES.ASSET_FEATURES"
    strategy_name = "MOMENTUM_STRATEGY"
    output_table = f"{db}.OUTPUT.TRADING_SIGNALS"
    
    # Run full pipeline
    result1 = feature_engineering_task(session, source_table, feature_view)
    logger.info(result1)
    
    result2 = strategy_registration_task(session, feature_view, strategy_name, "")
    logger.info(result2)
    
    result3 = signal_generation_task(session, feature_view, strategy_name, output_table)
    logger.info(result3)
    
    return "Investment strategy pipeline complete"


def feature_engineering_main(session: Session) -> str:
    """Entry point for Technical Indicators stored procedure."""
    db = session.get_current_database().strip('"')
    
    # Derive environment prefix from database name (e.g., DEV_ML_DB -> DEV)
    env_prefix = db.split("_")[0]
    
    # Source table is in RAW_DB, features are in ML_DB.FEATURES
    source_table = f"{env_prefix}_RAW_DB.PUBLIC.MARKET_DATA"
    feature_view = f"{db}.FEATURES.ASSET_FEATURES"
    
    return feature_engineering_task(session, source_table, feature_view)


def strategy_registration_main(session: Session) -> str:
    """Entry point for Strategy Registration stored procedure."""
    db = session.get_current_database().strip('"')
    
    feature_view = f"{db}.FEATURES.ASSET_FEATURES"
    strategy_name = "MOMENTUM_STRATEGY"
    
    return strategy_registration_task(session, feature_view, strategy_name, "")


def signal_generation_main(session: Session) -> str:
    """Entry point for Signal Generation stored procedure."""
    db = session.get_current_database().strip('"')
    
    feature_view = f"{db}.FEATURES.ASSET_FEATURES"
    strategy_name = "MOMENTUM_STRATEGY"
    output_table = f"{db}.OUTPUT.TRADING_SIGNALS"
    
    return signal_generation_task(session, feature_view, strategy_name, output_table)

