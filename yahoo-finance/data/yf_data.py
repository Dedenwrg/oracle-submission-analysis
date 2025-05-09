import os
import yfinance as yf

# Define currency pairs
fx_pairs = ["AUDUSD", "CADUSD", "EURUSD", "GBPUSD", "JPYUSD", "SEKUSD"]

# Define 1-minute interval date batches (start_date, end_date)
dates_1m_batches = [
    # ("2024-12-30", "2025-01-07"),
    # ("2025-01-07", "2025-01-14"),
    # ...
    # ("2025-04-08", "2025-04-15"),
    # ("2025-04-15", "2025-04-22"),
    #("2025-04-22", "2025-04-29"),
    ("2025-04-29", "2025-05-06"),
]

# Function to fetch and save FX data
def fetch_and_save_fx_data(pair: str, start_date: str, end_date: str, interval: str):
    """Fetch FX data from Yahoo Finance and save it as a CSV file."""
    data = yf.download(f"{pair}=X", start=start_date, end=end_date, interval=interval, 
    auto_adjust=False)

    # Ensure the directory exists
    pair_dir = f"./{pair}"
    os.makedirs(pair_dir, exist_ok=True)

    # Define the CSV file path
    csv_file_path = f"{pair_dir}/{pair}=X_{interval}_{start_date}_{end_date}.csv"
    
    # Save the data
    data.to_csv(csv_file_path)
    print(f"{pair} data saved to {csv_file_path}")


# Extract data for 1-minute interval
for pair in fx_pairs:
    for start_date, end_date in dates_1m_batches:
        fetch_and_save_fx_data(pair, start_date, end_date, "1m")

# Uncomment the following section to extract data for 5-minute intervals
# dates_5m_batches = [
#     ("2024-12-02", "2025-01-28")  # start_date, end_date
# ]
#
# for pair in fx_pairs:
#     for start_date, end_date in dates_5m_batches:
#         fetch_and_save_fx_data(pair, start_date, end_date, "5m")
