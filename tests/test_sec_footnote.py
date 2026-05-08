import responses as resp_mock
from worker.filter.sec_footnote import is_10b5_1_plan

@resp_mock.activate
def test_detects_10b5_1_in_footnote():
    resp_mock.add(
        resp_mock.GET,
        "https://www.sec.gov/Archives/test-filing.html",
        body="<html><body>F1: This transaction was made pursuant to a Rule 10b5-1 plan.</body></html>",
        status=200,
    )
    assert is_10b5_1_plan("https://www.sec.gov/Archives/test-filing.html") is True

@resp_mock.activate
def test_clean_filing_not_flagged():
    resp_mock.add(
        resp_mock.GET,
        "https://www.sec.gov/Archives/clean-filing.html",
        body="<html><body>Purchase on the open market.</body></html>",
        status=200,
    )
    assert is_10b5_1_plan("https://www.sec.gov/Archives/clean-filing.html") is False

@resp_mock.activate
def test_returns_false_on_fetch_error():
    resp_mock.add(
        resp_mock.GET,
        "https://www.sec.gov/Archives/bad-filing.html",
        status=500,
    )
    assert is_10b5_1_plan("https://www.sec.gov/Archives/bad-filing.html") is False

def test_returns_false_on_empty_url():
    assert is_10b5_1_plan("") is False
