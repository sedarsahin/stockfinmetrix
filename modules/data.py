import logging
import os
import datetime as dt
import pandas as pd
import pandas_datareader.nasdaq_trader as nas
import yfinance as yf
import requests
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global session
session = None

def get_nasdaq_symbols(cache_file='nasdaq_symbols.pkl'):
    """
    Retrieves NASDAQ symbols. Caches the result to a file to speed up subsequent loads.
    """
    if os.path.exists(cache_file):
        logger.info(f"Loading NASDAQ symbols from cache: {cache_file}")
        try:
            return pd.read_pickle(cache_file)
        except Exception as e:
            logger.error(f"Failed to load cache, fetching fresh data: {e}")
    
    logger.info("Fetching NASDAQ symbols from source...")
    try:
        nsdq = nas.get_nasdaq_symbols()
        
        # Filter data
        nsdq['Security Name'] = nsdq['Security Name'].str.replace(" Common Stock","").str.replace("-","").str.rstrip()
        nsdq_filtered = nsdq[~nsdq['Security Name'].str.contains('%')]
        nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('share')]
        nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('redeemable')]
        nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('exercise')]
        nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('representing')]
        nsdq_filtered = nsdq_filtered[~nsdq_filtered.index.isnull()]
        
        # Save to cache
        nsdq_filtered.to_pickle(cache_file)
        return nsdq_filtered
    except Exception as e:
        logger.error(f"Error fetching NASDAQ symbols: {e}")
        return pd.DataFrame() # Return empty DF on failure

def get_ticker_options():
    """Generates options for the dropdown menu."""
    nsdq_filtered = get_nasdaq_symbols()
    if nsdq_filtered.empty:
        return []
        
    options = []
    for tic in nsdq_filtered.index:
        try:
            # Ensure we have the security name, otherwise fallback to ticker
            name = nsdq_filtered.loc[tic]['Security Name'] if 'Security Name' in nsdq_filtered.columns else tic
            if isinstance(name, pd.Series): # Handle duplicate indices if any
                name = name.iloc[0]
                
            tic_dict = {}
            tic_dict['label'] = f"{name} - {tic}"
            tic_dict['value'] = tic
            options.append(tic_dict)
        except Exception as e:
            logger.warning(f"Skipping ticker {tic} due to error: {e}")
            continue
    return options

def fetch_stock_data(tickers, start_date, end_date):
    """Downloads stock data for given tickers."""
    start = dt.datetime.strptime(start_date[:10],'%Y-%m-%d')
    end = dt.datetime.strptime(end_date[:10],'%Y-%m-%d')

    traces = []
    for tic in tickers:
        try:
            df = yf.download(tic, 
                             start=start, 
                             end=end, 
                             threads=False, 
                             progress=False)
            logger.info(f"Columns for {tic}: {df.columns}")
            if not df.empty:
                # Handle MultiIndex (Price, Ticker)
                if isinstance(df.columns, pd.MultiIndex):
                    try:
                        # Access Close price
                        if 'Close' in df.columns.get_level_values(0):
                             y_data = df['Close']
                             # If it's a DataFrame, it means we have a ticker level
                             if isinstance(y_data, pd.DataFrame):
                                 if tic in y_data.columns:
                                     y_data = y_data[tic]
                                 else:
                                     # Fallback: take the first column if ticker mismatch
                                     y_data = y_data.iloc[:, 0]
                    except Exception as e:
                         logger.error(f"Error parsing multiindex: {e}")
                         y_data = df['Close'] # Fallback
                else:
                    # Single index
                    if 'Close' in df.columns:
                        y_data = df['Close']
                    else:
                        # Fallback if auto_adjust=True might rename columns? 
                        # Usually it's still Close but let's be safe
                        y_data = df.iloc[:, 0] 
                
                traces.append({'x':df.index, 'y':y_data, 'name':tic})
            else:
                logger.warning(f"No data found for {tic}")
        except Exception as e:
            logger.error(f"Error downloading data for {tic}: {e}")
            pass # Keep passing to allow other tickers to load
            
    return traces

import requests

def create_session():
    """Creates a session with custom headers to avoid 429 errors."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

# Global session
session = create_session()

def get_ticker_info_data(symbol):
    """Fetches ticker info."""
    try:
        # Pass the session to Ticker
        return yf.Ticker(symbol).info
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {e}")
        return None

def get_income_stmt(symbol, quarterly=False):
    """Fetches income statement."""
    try:
        ticker = yf.Ticker(symbol)
        if quarterly:
            return ticker.quarterly_income_stmt
        return ticker.income_stmt
    except Exception as e:
        logger.error(f"Error fetching income statement for {symbol} (Quarterly={quarterly}): {e}")
        return pd.DataFrame()

def get_balance_sheet(symbol, quarterly=False):
    """Fetches balance sheet."""
    try:
        ticker = yf.Ticker(symbol)
        if quarterly:
            return ticker.quarterly_balance_sheet
        return ticker.balance_sheet
    except Exception as e:
        logger.error(f"Error fetching balance sheet for {symbol} (Quarterly={quarterly}): {e}")
        return pd.DataFrame()

def get_cashflow(symbol, quarterly=False):
    """Fetches cash flow statement."""
    try:
        ticker = yf.Ticker(symbol)
        if quarterly:
            return ticker.quarterly_cashflow
        return ticker.cashflow
    except Exception as e:
        logger.error(f"Error fetching cash flow for {symbol} (Quarterly={quarterly}): {e}")
        return pd.DataFrame()

def get_dividends(symbol):
    """Fetches dividend history."""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.dividends
    except Exception as e:
        logger.error(f"Error fetching dividends for {symbol}: {e}")
        return pd.Series()
