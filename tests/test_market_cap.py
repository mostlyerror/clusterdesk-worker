from unittest.mock import MagicMock, patch
from worker.filter.market_cap import get_market_cap

@patch("worker.filter.market_cap.yf.Ticker")
def test_fetches_from_yfinance_on_cache_miss(mock_ticker):
    mock_db = MagicMock()
    mock_db.get_market_cap_cache.return_value = None
    mock_ticker.return_value.info = {"marketCap": 150_000_000}

    result = get_market_cap("ACME", db=mock_db)

    assert result == 150_000_000
    mock_db.set_market_cap_cache.assert_called_once_with("ACME", 150_000_000)

def test_returns_cached_value():
    mock_db = MagicMock()
    mock_db.get_market_cap_cache.return_value = 200_000_000

    result = get_market_cap("ACME", db=mock_db)

    assert result == 200_000_000

@patch("worker.filter.market_cap.yf.Ticker")
def test_returns_none_on_yfinance_failure(mock_ticker):
    mock_db = MagicMock()
    mock_db.get_market_cap_cache.return_value = None
    mock_ticker.return_value.info = {}

    result = get_market_cap("ACME", db=mock_db)

    assert result is None
