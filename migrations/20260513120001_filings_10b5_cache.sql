ALTER TABLE filings ADD COLUMN IF NOT EXISTS is_10b5_1 BOOLEAN;
CREATE INDEX IF NOT EXISTS idx_filings_filing_url ON filings (filing_url);
