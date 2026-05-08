from datetime import date, datetime
from unittest.mock import MagicMock, patch
from worker.types import Filing
from worker.filter.rules import apply_filters

def make_filing(**kwargs) -> Filing:
    defaults = dict(
        filing_date=date(2026, 1, 10), trade_date=date(2026, 1, 8),
        ticker="ACME", company_name="Acme Corp", insider_name="Jane",
        insider_title="CEO", transaction_code="P", shares=10000,
        price_per_share=5.50, trade_value_usd=55000,
        shares_owned_after=50000, ownership_change_pct=25.0,
        filing_url="https://sec.gov/1", scraped_at=datetime.now(),
    )
    defaults.update(kwargs)
    return Filing(**defaults)

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_valid_filing_passes(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing()], db=mock_db)
    assert len(result) == 1

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_sale_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing(transaction_code="S")], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_trade_below_25k_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing(trade_value_usd=10000)], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_penny_stock_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing(price_per_share=1.50)], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=600_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_large_cap_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing()], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=30_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_micro_cap_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing()], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=True)
def test_10b5_plan_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing()], db=mock_db)
    assert result == []

@patch("worker.filter.rules.get_market_cap", return_value=200_000_000)
@patch("worker.filter.rules.is_10b5_1_plan", return_value=False)
def test_option_exercise_excluded(mock_10b5, mock_mcap):
    mock_db = MagicMock()
    result = apply_filters([make_filing(transaction_code="M")], db=mock_db)
    assert result == []
