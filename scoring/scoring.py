"""
Oracle Scoring Script for Tiber Challenge
Processes validator submissions against benchmark data to calculate scores
"""

import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import warnings

warnings.filterwarnings("ignore")

# Constants
ACU_PAIRS = ["AUD-USD", "CAD-USD", "EUR-USD", "GBP-USD", "JPY-USD", "SEK-USD"]
CRYPTO_PAIRS = ["ATN-USD", "NTN-USD"]
M_FX = 2.0  # FX accuracy multiplier
M_CRYPTO = 2.0  # Crypto accuracy multiplier

# Configuration flags
ADJUST_FOR_PRICE_DISCREPANCY = True  # Set to True to adjust for ~50% discrepancy
PRICE_ADJUSTMENT_FACTOR = (
    2.0  # Factor to multiply submission prices if discrepancy detected
)

# Paths
BASE_DIR = Path(".")
SUBMISSION_DIR = BASE_DIR / "submission-data"
YAHOO_DIR = BASE_DIR / "yahoo-finance"
USDC_USD_DIR = BASE_DIR / "usdc-usd-data"
SWAP_DIR = BASE_DIR / "swap-data"
SCORING_DIR = BASE_DIR / "scoring"
INTERMEDIATE_DIR = SCORING_DIR / "intermediate"

# Create intermediate directory if not exists
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

# Debug flag
DEBUG = False  # Set to True for detailed debugging

# Configuration flags
ADJUST_FOR_PRICE_DISCREPANCY = True  # Set to True to adjust for ~50% discrepancy
PRICE_ADJUSTMENT_FACTOR = (
    2.0  # Factor to multiply submission prices if discrepancy detected
)


def debug_check_yahoo_file():
    """Debug function to check Yahoo Finance file format"""
    if DEBUG:
        # Try to find and read a sample Yahoo file
        sample_file = None
        yahoo_data_dir = YAHOO_DIR / "data"
        if yahoo_data_dir.exists():
            for pair_dir in yahoo_data_dir.iterdir():
                if pair_dir.is_dir():
                    files = list(pair_dir.glob("*.csv"))
                    if files:
                        sample_file = files[0]
                        break

        if sample_file:
            print(f"\nDEBUG: Checking Yahoo Finance file format: {sample_file}")
            try:
                # Read first 10 lines
                with open(sample_file, "r") as f:
                    lines = [f.readline().strip() for _ in range(10)]

                print("First 10 lines:")
                for i, line in enumerate(lines):
                    print(f"  Line {i}: {line}")

                # Try reading with pandas
                df_test = pd.read_csv(sample_file)
                print(f"\nColumns without skiprows: {df_test.columns.tolist()}")
                print(f"Shape: {df_test.shape}")

                # Try with skiprows=2
                df_test2 = pd.read_csv(sample_file, skiprows=2)
                print(f"\nColumns with skiprows=2: {df_test2.columns.tolist()}")
                print(f"Shape: {df_test2.shape}")

            except Exception as e:
                print(f"Error reading sample file: {e}")


def load_progress():
    """Load progress from intermediate file"""
    progress_file = INTERMEDIATE_DIR / "progress.json"
    if progress_file.exists():
        with open(progress_file, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    """Save progress to intermediate file"""
    progress_file = INTERMEDIATE_DIR / "progress.json"
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)


def load_submission_data(date_str):
    """Load oracle submission data for a specific date"""
    filename = f"Oracle_Submission_{date_str}.csv"
    filepath = SUBMISSION_DIR / filename

    if not filepath.exists():
        print(f"Warning: Submission file not found: {filepath}")
        return pd.DataFrame()

    print(f"Loading submission data: {filename}")
    df = pd.read_csv(filepath)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True)

    if DEBUG:
        print(
            f"  Submission time range: {df['Timestamp'].min()} to {df['Timestamp'].max()}"
        )
        print("  Sample submission prices (first 5):")
        for pair in ACU_PAIRS[:2]:  # Show first 2 FX pairs
            col = f"{pair} Price"
            if col in df.columns:
                sample_prices = df[col].dropna().head()
                if len(sample_prices) > 0:
                    print(
                        f"    {pair}: {sample_prices.iloc[0]/1e18:.6f} (wei: {sample_prices.iloc[0]})"
                    )

        # Also show crypto pairs
        for pair in CRYPTO_PAIRS:
            col = f"{pair} Price"
            if col in df.columns:
                sample_prices = df[col].dropna().head(3)
                if len(sample_prices) > 0:
                    print(f"    {pair} samples:")
                    for i, price in enumerate(sample_prices):
                        print(f"      [{i}] {price/1e18:.6f} (wei: {price})")

    return df


def load_yahoo_finance_data(pair, date):
    """Load Yahoo Finance data for a specific pair around the given date"""
    # Map pair format
    pair_map = {
        "AUD-USD": "AUDUSD",
        "CAD-USD": "CADUSD",
        "EUR-USD": "EURUSD",
        "GBP-USD": "GBPUSD",
        "JPY-USD": "JPYUSD",
        "SEK-USD": "SEKUSD",
    }

    yahoo_pair = pair_map.get(pair)
    if not yahoo_pair:
        return pd.DataFrame()

    # Find relevant files for the date
    yahoo_pair_dir = YAHOO_DIR / "data" / yahoo_pair
    if not yahoo_pair_dir.exists():
        print(f"Warning: Yahoo data directory not found: {yahoo_pair_dir}")
        return pd.DataFrame()

    all_data = []
    for file in yahoo_pair_dir.glob(f"{yahoo_pair}=X_*.csv"):
        if DEBUG:
            print(f"    Checking file: {file.name}")

        try:
            # Read the special Yahoo Finance format
            # Line 0: Price,Close,High,Low,Open,Volume
            # Line 1: Ticker,AUDUSD=X,AUDUSD=X,AUDUSD=X,AUDUSD=X,AUDUSD=X
            # Line 2: Datetime,,,,,
            # Line 3+: actual data

            # Read the file to get column mapping
            with open(file, "r") as f:
                header_line = f.readline().strip()  # Price,Close,High,Low,Open,Volume
                _ = f.readline().strip()  # Ticker line
                _ = f.readline().strip()  # Datetime line

            # Parse column names from header
            column_names = header_line.split(",")

            # Read the data starting from line 3
            df = pd.read_csv(file, skiprows=3, header=None)

            # Set column names based on the header structure
            # First column is Datetime, rest map to Price header
            df.columns = ["Datetime"] + column_names[
                1:6
            ]  # Close, High, Low, Open, Volume

            # Parse datetime
            df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)

            # Ensure we have required columns
            required_cols = ["Datetime", "Open", "High", "Low", "Close"]
            if not all(col in df.columns for col in required_cols):
                if DEBUG:
                    print(f"      Missing required columns in {file.name}")
                continue

        except Exception as e:
            if DEBUG:
                print(f"      Error reading {file.name}: {e}")
            continue

        # Check if date is within this file's range
        if len(df) > 0:
            file_start = df["Datetime"].min().date()
            file_end = df["Datetime"].max().date()
            if DEBUG:
                print(f"      File date range: {file_start} to {file_end}")

            if file_start <= date.date() <= file_end:
                all_data.append(df)
                if DEBUG:
                    print("      ✓ File contains target date")
                    print(
                        f"      Sample data: O={df.iloc[0]['Open']:.6f}, C={df.iloc[0]['Close']:.6f}"
                    )

    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result = result.sort_values("Datetime")

        if DEBUG:
            print(f"    Loaded {len(result)} OHLC intervals")
            print(
                f"    Time range: {result['Datetime'].min()} to {result['Datetime'].max()}"
            )
            print(
                f"    Sample OHLC (first row): O={result.iloc[0]['Open']:.6f}, H={result.iloc[0]['High']:.6f}, L={result.iloc[0]['Low']:.6f}, C={result.iloc[0]['Close']:.6f}"
            )

        return result

    return pd.DataFrame()


def load_usdc_usd_data():
    """Load USDC-USD data from Kraken"""
    filepath = USDC_USD_DIR / "USDCUSD_1.csv"
    if not filepath.exists():
        print(f"Warning: USDC-USD file not found: {filepath}")
        return pd.DataFrame()

    # Kraken data format: timestamp,open,high,low,close,volume,count
    df = pd.read_csv(
        filepath,
        header=None,
        names=["timestamp", "open", "high", "low", "close", "volume", "count"],
    )
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)

    if DEBUG:
        print(f"  Loaded {len(df)} USDC-USD price points")
        print(f"  Time range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"  Sample prices: {df['close'].head().tolist()}")

    return df


def load_swap_data(pair, date):
    """Load swap data for ATN/USDC or NTN/USDC"""
    pair_map = {"ATN-USD": "atn-usdc", "NTN-USD": "ntn-usdc"}

    swap_pair = pair_map.get(pair)
    if not swap_pair:
        return pd.DataFrame()

    swap_pair_dir = SWAP_DIR / swap_pair
    if not swap_pair_dir.exists():
        print(f"Warning: Swap data directory not found: {swap_pair_dir}")
        return pd.DataFrame()

    # Find file for the date
    date_str = date.strftime("%Y-%m-%d")
    filepath = swap_pair_dir / f"{swap_pair}-{date_str}.csv"

    if not filepath.exists():
        # Try to find any file that might contain this date
        all_files = list(swap_pair_dir.glob(f"{swap_pair}-*.csv"))
        for file in sorted(all_files):
            df = pd.read_csv(file)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            if len(df) > 0:
                file_date = df["timestamp"].iloc[0].date()
                if file_date == date.date():
                    if DEBUG:
                        print(f"    Found swap data in file: {file.name}")
                        print(f"    Loaded {len(df)} price points")
                        print(f"    Sample prices: {df['price'].head().tolist()}")
                    return df
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    if DEBUG:
        print(f"    Loaded {len(df)} price points from {filepath.name}")
        print(f"    Sample prices: {df['price'].head().tolist()}")

    return df


def calculate_fx_volatility(yahoo_data):
    """Calculate annualized volatility for FX pairs"""
    if len(yahoo_data) == 0:
        return 0.0

    # Get daily close prices
    daily_closes = yahoo_data.groupby(yahoo_data["Datetime"].dt.date)["Close"].last()

    if len(daily_closes) < 2:
        if DEBUG:
            print(f"      Not enough daily closes for volatility: {len(daily_closes)}")
        return 0.0

    # Calculate log returns
    log_returns = np.log(daily_closes / daily_closes.shift(1))
    log_returns = log_returns.dropna()

    if len(log_returns) == 0:
        return 0.0

    # Annualized volatility (252 trading days)
    volatility = log_returns.std() * np.sqrt(252)

    if DEBUG:
        print(
            f"      Daily closes: {len(daily_closes)}, Log returns: {len(log_returns)}"
        )
        print(
            f"      Volatility calculation: std={log_returns.std():.6f}, annualized={volatility:.6f}"
        )

    return volatility


def get_crypto_price_at_timestamp(swap_data, usdc_usd_data, timestamp):
    """Get crypto price at a specific timestamp"""
    # Get swap price at timestamp (constant extrapolation)
    swap_prices = swap_data[swap_data["timestamp"] <= timestamp]
    if len(swap_prices) == 0:
        return None

    swap_price = swap_prices.iloc[-1]["price"]

    # Get USDC/USD price (backward extrapolation of close)
    usdc_prices = usdc_usd_data[usdc_usd_data["datetime"] <= timestamp]
    if len(usdc_prices) == 0:
        return None

    usdc_price = usdc_prices.iloc[-1]["close"]

    # Calculate price in USD
    return swap_price * usdc_price


def calculate_crypto_volatility(swap_data, usdc_usd_data):
    """Calculate annualized volatility for crypto pairs"""
    if len(swap_data) == 0 or len(usdc_usd_data) == 0:
        return 0.0

    # Calculate daily prices
    daily_prices = []
    dates = pd.date_range(
        swap_data["timestamp"].min().date(),
        swap_data["timestamp"].max().date(),
        freq="D",
    )

    for date in dates:
        end_of_day = pd.Timestamp(date, tz="UTC").replace(hour=23, minute=59, second=59)
        price = get_crypto_price_at_timestamp(swap_data, usdc_usd_data, end_of_day)
        if price:
            daily_prices.append(price)

    if len(daily_prices) < 2:
        return 0.0

    # Calculate log returns
    prices = pd.Series(daily_prices)
    log_returns = np.log(prices / prices.shift(1))
    log_returns = log_returns.dropna()

    if len(log_returns) == 0:
        return 0.0

    # Annualized volatility (365 days)
    return log_returns.std() * np.sqrt(365)


def investigate_price_discrepancy(submissions_df, swap_data, usdc_usd_data, pair):
    """Investigate the price discrepancy between submissions and benchmarks"""
    if not DEBUG or len(swap_data) == 0 or len(usdc_usd_data) == 0:
        return

    price_col = f"{pair} Price"
    if price_col not in submissions_df.columns:
        return

    print(f"\n    INVESTIGATING PRICE DISCREPANCY for {pair}:")

    # Sample 10 different timestamps
    sample_df = submissions_df[submissions_df[price_col].notna()].sample(
        min(10, len(submissions_df))
    )

    ratios = []
    for _, row in sample_df.iterrows():
        submission_price = row[price_col] / 1e18
        timestamp = row["Timestamp"]

        benchmark = get_crypto_price_at_timestamp(swap_data, usdc_usd_data, timestamp)
        if benchmark:
            ratio = submission_price / benchmark
            ratios.append(ratio)

            if len(ratios) <= 3:  # Show first 3
                print(f"      Time: {timestamp}")
                print(f"        Submission: {submission_price:.6f}")
                print(f"        Benchmark: {benchmark:.6f}")
                print(f"        Ratio: {ratio:.6f}")

    if ratios:
        avg_ratio = np.mean(ratios)
        std_ratio = np.std(ratios)
        print(f"\n      Average ratio: {avg_ratio:.6f} (std: {std_ratio:.6f})")

        # Check if it's consistently around 0.5
        if 0.48 < avg_ratio < 0.53:
            print("        WARNING: Submissions appear to be ~50% of benchmark!")
            print("      This suggests a systematic issue with submission data.")

        return avg_ratio

    return None


def score_fx_submissions_vectorized(
    submissions_df, pair, yahoo_data, sigma, interval_seconds
):
    """Score FX submissions using vectorized operations"""
    if len(yahoo_data) == 0:
        if DEBUG:
            print("      No Yahoo data available")
        return pd.Series(0, index=submissions_df.index)

    if sigma == 0:
        if DEBUG:
            print("      Zero volatility, using default 0.05")
        sigma = 0.05  # Default volatility if calculation fails

    price_col = f"{pair} Price"
    if price_col not in submissions_df.columns:
        return pd.Series(0, index=submissions_df.index)

    # Convert prices from wei
    prices = submissions_df[price_col] / 1e18
    timestamps = submissions_df["Timestamp"]

    # Initialize scores
    scores = pd.Series(0, index=submissions_df.index)

    # Time scaling factor
    time_factor = np.sqrt(interval_seconds / (365 * 24 * 60 * 60))

    if DEBUG:
        print(f"      Time factor: {time_factor:.8f}")
        submissions_in_intervals = 0
        valid_submissions = 0

    # Process each OHLC interval
    for i, ohlc in yahoo_data.iterrows():
        interval_end = ohlc["Datetime"]
        interval_start = interval_end - pd.Timedelta(seconds=interval_seconds)

        # Find submissions in this interval
        mask = (timestamps > interval_start) & (timestamps <= interval_end)

        if mask.any():
            # Calculate bounds for this interval
            open_price = ohlc["Open"]
            lower_bound = ohlc["Low"] - M_FX * sigma * time_factor * open_price
            upper_bound = ohlc["High"] + M_FX * sigma * time_factor * open_price

            # Score submissions in this interval
            interval_prices = prices[mask]
            valid_prices = ~interval_prices.isna()
            within_bounds = (interval_prices >= lower_bound) & (
                interval_prices <= upper_bound
            )

            # Update scores
            new_scores = mask & valid_prices & within_bounds
            scores.loc[new_scores] = 1

            if DEBUG and i < 3:  # Show first 3 intervals
                num_in_interval = mask.sum()
                num_valid = (mask & valid_prices).sum()
                num_within_bounds = new_scores.sum()

                print(f"      Interval {i}: {interval_start} to {interval_end}")
                print(
                    f"        OHLC: O={open_price:.6f}, H={ohlc['High']:.6f}, L={ohlc['Low']:.6f}"
                )
                print(f"        Bounds: [{lower_bound:.6f}, {upper_bound:.6f}]")
                print(
                    f"        Submissions: {num_in_interval} total, {num_valid} valid, {num_within_bounds} within bounds"
                )

                if num_valid > 0:
                    sample_price = interval_prices[valid_prices].iloc[0]
                    print(f"        Sample submission price: {sample_price:.6f}")

            if DEBUG:
                submissions_in_intervals += mask.sum()
                valid_submissions += new_scores.sum()

    if DEBUG:
        print(
            f"      Total: {submissions_in_intervals} submissions matched intervals, {valid_submissions} scored 1"
        )

    return scores


def score_crypto_submissions_vectorized(
    submissions_df, pair, swap_data, usdc_usd_data, sigma, discrepancy_ratio=None
):
    """Score crypto submissions using vectorized operations"""
    if len(swap_data) == 0 or len(usdc_usd_data) == 0:
        if DEBUG:
            print("      No swap or USDC data available")
        return pd.Series(0, index=submissions_df.index)

    if sigma == 0:
        if DEBUG:
            print("      Zero volatility, using default 0.1")
        sigma = 0.1  # Default volatility for crypto

    price_col = f"{pair} Price"
    if price_col not in submissions_df.columns:
        return pd.Series(0, index=submissions_df.index)

    # Convert prices from wei
    prices = submissions_df[price_col] / 1e18

    # Adjust for price discrepancy if detected and configured
    if (
        ADJUST_FOR_PRICE_DISCREPANCY
        and discrepancy_ratio
        and 0.48 < discrepancy_ratio < 0.53
    ):
        if DEBUG:
            print(
                f"      Adjusting submission prices by factor of {PRICE_ADJUSTMENT_FACTOR} due to detected discrepancy"
            )
        prices = prices * PRICE_ADJUSTMENT_FACTOR

    timestamps = submissions_df["Timestamp"]

    # Initialize scores
    scores = pd.Series(0, index=submissions_df.index)

    # Time scaling factor (30 seconds)
    time_factor = np.sqrt(30 / (365 * 24 * 60 * 60))

    # Create benchmark price series for all unique timestamps
    unique_timestamps = timestamps.unique()
    benchmark_prices = {}

    if DEBUG:
        print(
            f"      Calculating benchmarks for {len(unique_timestamps)} unique timestamps..."
        )

    # Calculate all benchmarks
    for i, ts in enumerate(unique_timestamps):
        if i % 500 == 0 and i > 0:
            print(
                f"\r      Progress: {i}/{len(unique_timestamps)} benchmarks calculated...",
                end="",
                flush=True,
            )
        price = get_crypto_price_at_timestamp(swap_data, usdc_usd_data, ts)
        if price:
            benchmark_prices[ts] = price

    if DEBUG:
        print(f"\n      Calculated {len(benchmark_prices)} benchmark prices")
        if benchmark_prices:
            sample_prices = list(benchmark_prices.values())[:3]
            print(f"      Sample benchmark prices: {sample_prices}")

    # Map benchmark prices to submissions
    benchmarks = timestamps.map(benchmark_prices)

    # Calculate bounds
    valid_benchmarks = ~benchmarks.isna()
    lower_bounds = benchmarks * (1 - M_CRYPTO * sigma * time_factor)
    upper_bounds = benchmarks * (1 + M_CRYPTO * sigma * time_factor)

    # Score submissions
    valid_prices = ~prices.isna()
    within_bounds = (prices >= lower_bounds) & (prices <= upper_bounds)

    scores.loc[valid_benchmarks & valid_prices & within_bounds] = 1

    if DEBUG:
        num_valid_benchmarks = valid_benchmarks.sum()
        num_valid_prices = (valid_benchmarks & valid_prices).sum()
        num_within_bounds = scores.sum()

        print(f"      Valid benchmarks: {num_valid_benchmarks}")
        print(f"      Valid prices: {num_valid_prices}")
        print(f"      Within bounds: {num_within_bounds}")

        # Show multiple sample comparisons
        valid_idx = valid_benchmarks & valid_prices
        if valid_idx.any():
            sample_indices = valid_idx[valid_idx].index[
                :5
            ]  # Show first 5 valid comparisons
            print("\n      Sample comparisons:")
            for idx in sample_indices:
                adjusted_indicator = (
                    " (adjusted)"
                    if ADJUST_FOR_PRICE_DISCREPANCY
                    and discrepancy_ratio
                    and 0.48 < discrepancy_ratio < 0.53
                    else ""
                )
                print(f"        Index {idx}:")
                print(
                    f"          Submission price: {prices[idx]:.6f}{adjusted_indicator}"
                )
                print(f"          Benchmark: {benchmarks[idx]:.6f}")
                print(
                    f"          Bounds: [{lower_bounds[idx]:.6f}, {upper_bounds[idx]:.6f}]"
                )
                print(f"          Within bounds: {within_bounds[idx]}")

    return scores


def process_date(date_str):
    """Process submissions for a single date"""
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"Processing date: {date_str}")
    print(f"{'='*60}")

    # Load submission data
    submissions = load_submission_data(date_str)
    if len(submissions) == 0:
        print(f"No submissions found for {date_str}")
        return pd.DataFrame()

    print(
        f"Found {len(submissions)} submissions from {submissions['Validator Address'].nunique()} validators"
    )

    # Parse date
    date = pd.to_datetime(date_str, utc=True)

    # Determine interval for FX pairs
    if date < pd.Timestamp("2025-01-28", tz="UTC"):
        interval_seconds = 300  # 5 minutes
    else:
        interval_seconds = 60  # 1 minute

    print(f"Using {interval_seconds}s intervals for FX pairs")

    # Load USDC-USD data once
    print("\nLoading USDC-USD data...")
    usdc_usd_data = load_usdc_usd_data()

    # Pre-load all data for this date
    print("\nLoading market data for all pairs...")
    fx_data = {}
    fx_volatilities = {}

    # Check if this is in the first period (special 5m file handling)
    is_first_period = date < pd.Timestamp("2025-01-28", tz="UTC")

    for pair in ACU_PAIRS:
        print(f"\n  Loading {pair}...")
        data = load_yahoo_finance_data(pair, date)
        if len(data) > 0:
            fx_data[pair] = data
            fx_volatilities[pair] = calculate_fx_volatility(data)
            print(
                f"  {pair}: {len(data)} intervals, volatility={fx_volatilities[pair]:.4f}"
            )
        else:
            # If no data found and it's first period, check for the special 5m file
            if is_first_period and DEBUG:
                print(
                    f"  No data found for {pair} on {date_str}. Note: First period uses 5m intervals."
                )

    crypto_data = {}
    crypto_volatilities = {}
    crypto_discrepancy_ratios = {}
    for pair in CRYPTO_PAIRS:
        print(f"\n  Loading {pair}...")
        data = load_swap_data(pair, date)
        if len(data) > 0:
            crypto_data[pair] = data
            crypto_volatilities[pair] = calculate_crypto_volatility(data, usdc_usd_data)
            print(
                f"  {pair}: {len(data)} prices, volatility={crypto_volatilities[pair]:.4f}"
            )

            # Investigate price discrepancy
            if DEBUG:
                ratio = investigate_price_discrepancy(
                    submissions, data, usdc_usd_data, pair
                )
                if ratio:
                    crypto_discrepancy_ratios[pair] = ratio

    # Initialize validator scores
    validator_scores = {
        v: {p: 0 for p in ACU_PAIRS + CRYPTO_PAIRS}
        for v in submissions["Validator Address"].unique()
    }

    # Process FX pairs
    print("\n\nScoring FX pairs...")
    for pair in ACU_PAIRS:
        if pair in fx_data:
            print(f"\n  Processing {pair}...")
            pair_scores = score_fx_submissions_vectorized(
                submissions,
                pair,
                fx_data[pair],
                fx_volatilities[pair],
                interval_seconds,
            )

            # Aggregate by validator
            for idx, score in pair_scores[pair_scores > 0].items():
                validator = submissions.loc[idx, "Validator Address"]
                validator_scores[validator][pair] += score

            print(f"  {pair}: {int(pair_scores.sum())} valid submissions")

    # Process crypto pairs
    print("\n\nScoring crypto pairs...")
    for pair in CRYPTO_PAIRS:
        if pair in crypto_data:
            print(f"\n  Processing {pair}...")
            discrepancy_ratio = crypto_discrepancy_ratios.get(pair)
            pair_scores = score_crypto_submissions_vectorized(
                submissions,
                pair,
                crypto_data[pair],
                usdc_usd_data,
                crypto_volatilities[pair],
                discrepancy_ratio,
            )

            # Aggregate by validator
            for idx, score in pair_scores[pair_scores > 0].items():
                validator = submissions.loc[idx, "Validator Address"]
                validator_scores[validator][pair] += score

            print(f"  {pair}: {int(pair_scores.sum())} valid submissions")

    # Convert to DataFrame
    results = []
    for validator, scores in validator_scores.items():
        row = {
            "validator": validator,
            "date": date_str,
            "total_score": sum(scores.values()),
        }
        for pair, score in scores.items():
            row[f"{pair}_score"] = score
        results.append(row)

    results_df = pd.DataFrame(results)

    # Save intermediate results
    intermediate_file = INTERMEDIATE_DIR / f"scores_{date_str}.csv"
    results_df.to_csv(intermediate_file, index=False)

    elapsed = time.time() - start_time
    print(f"\n\nProcessing completed in {elapsed:.1f} seconds")
    print(f"Saved intermediate results to: {intermediate_file}")

    # Print summary
    print("\nScoring Summary:")
    total_with_scores = (results_df["total_score"] > 0).sum()
    print(f"  Validators with positive scores: {total_with_scores}/{len(results_df)}")
    if total_with_scores > 0:
        print(
            f"  Average score (non-zero): {results_df[results_df['total_score'] > 0]['total_score'].mean():.2f}"
        )
        print(f"  Max score: {results_df['total_score'].max()}")

    return results_df


def main():
    """Main execution function"""
    global DEBUG

    # Check for debug flag
    if "--debug" in sys.argv:
        DEBUG = True
        sys.argv.remove("--debug")

    if DEBUG:
        print("Oracle Scoring Script (Debug Mode)")
    else:
        print("Oracle Scoring Script (Optimized)")
    print("=" * 60)

    # Debug check Yahoo file format
    if DEBUG:
        debug_check_yahoo_file()

    # Check if running with a specific date argument
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        results = process_date(date_str)

        # Save final results
        if len(results) > 0:
            output_file = SCORING_DIR / f"final_scores_{date_str}.csv"
            results.to_csv(output_file, index=False)
            print(f"\nFinal scores saved to: {output_file}")

            # Print summary
            print(f"\nSummary for {date_str}:")
            print(f"Total validators: {len(results)}")
            print(f"Average score: {results['total_score'].mean():.2f}")
            print(f"Max score: {results['total_score'].max()}")
            print(
                f"Validators with positive score: {(results['total_score'] > 0).sum()}"
            )
    else:
        # Process all available dates
        submission_files = sorted(SUBMISSION_DIR.glob("Oracle_Submission_*.csv"))

        if len(submission_files) == 0:
            print("No submission files found!")
            return

        print(f"Found {len(submission_files)} submission files to process")

        # Load progress
        progress = load_progress()

        all_results = []
        total_start_time = time.time()

        for i, file in enumerate(submission_files):
            # Extract date from filename
            date_str = file.stem.replace("Oracle_Submission_", "")

            # Skip if already processed
            if date_str in progress.get("completed_dates", []):
                print(f"Skipping {date_str} (already processed)")
                # Load existing results
                intermediate_file = INTERMEDIATE_DIR / f"scores_{date_str}.csv"
                if intermediate_file.exists():
                    all_results.append(pd.read_csv(intermediate_file))
                continue

            print(f"\nProgress: {i+1}/{len(submission_files)}")

            # Estimate remaining time
            if i > 0:
                elapsed = time.time() - total_start_time
                avg_time_per_file = elapsed / i
                remaining_files = len(submission_files) - i
                est_remaining = avg_time_per_file * remaining_files
                print(f"Estimated time remaining: {est_remaining/60:.1f} minutes")

            try:
                results = process_date(date_str)
                if len(results) > 0:
                    all_results.append(results)

                # Update progress
                if "completed_dates" not in progress:
                    progress["completed_dates"] = []
                progress["completed_dates"].append(date_str)
                save_progress(progress)

            except Exception as e:
                print(f"Error processing {date_str}: {e}")
                import traceback

                traceback.print_exc()
                continue

        # Combine all results
        if all_results:
            final_results = pd.concat(all_results, ignore_index=True)

            # Aggregate by validator
            validator_totals = (
                final_results.groupby("validator")["total_score"].sum().reset_index()
            )
            validator_totals = validator_totals.sort_values(
                "total_score", ascending=False
            )

            # Save final aggregated results
            output_file = SCORING_DIR / "final_scores_all.csv"
            validator_totals.to_csv(output_file, index=False)
            print(f"\n{'='*60}")
            print(f"Final aggregated scores saved to: {output_file}")

            # Calculate rewards (75000 total)
            total_rewards = 75000
            total_score = validator_totals["total_score"].sum()
            if total_score > 0:
                validator_totals["rewards"] = (
                    validator_totals["total_score"] * total_rewards / total_score
                )

                # Save with rewards
                rewards_file = SCORING_DIR / "validator_rewards.csv"
                validator_totals.to_csv(rewards_file, index=False)
                print(f"Validator rewards saved to: {rewards_file}")

                # Print summary
                print("\nFinal Summary:")
                print(f"Total validators: {len(validator_totals)}")
                print(
                    f"Validators with positive score: {(validator_totals['total_score'] > 0).sum()}"
                )
                print(f"Total score points: {total_score:.0f}")
                print(f"Average reward: {validator_totals['rewards'].mean():.2f}")
                print("\nTop 10 validators:")
                print(
                    validator_totals.head(10)[
                        ["validator", "total_score", "rewards"]
                    ].to_string(index=False)
                )

        total_elapsed = time.time() - total_start_time
        print(f"\n{'='*60}")
        print(f"Total processing time: {total_elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
