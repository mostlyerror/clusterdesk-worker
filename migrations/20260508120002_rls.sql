-- Enable RLS on all tables
ALTER TABLE filings ENABLE ROW LEVEL SECURITY;
ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticker_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_cap_cache ENABLE ROW LEVEL SECURITY;

-- Public read access for web app (anon key)
DROP POLICY IF EXISTS "public_read_filings" ON filings;
CREATE POLICY "public_read_filings"
    ON filings FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_clusters" ON clusters;
CREATE POLICY "public_read_clusters"
    ON clusters FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_ticker_pages" ON ticker_pages;
CREATE POLICY "public_read_ticker_pages"
    ON ticker_pages FOR SELECT USING (true);

-- Email subscribers: allow anon insert (web email capture form)
DROP POLICY IF EXISTS "anon_insert_subscribers" ON email_subscribers;
CREATE POLICY "anon_insert_subscribers"
    ON email_subscribers FOR INSERT WITH CHECK (true);

-- market_cap_cache: worker only (service role bypasses RLS, no anon access needed)
-- No policy = no anon access
