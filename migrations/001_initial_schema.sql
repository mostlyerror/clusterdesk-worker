CREATE TABLE filings (
    id SERIAL PRIMARY KEY,
    filing_date DATE NOT NULL,
    trade_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    insider_name TEXT NOT NULL,
    insider_title TEXT,
    transaction_code TEXT NOT NULL,
    shares INT,
    price_per_share NUMERIC(10,4),
    trade_value_usd INT,
    filing_url TEXT,
    raw_payload JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, insider_name, trade_date, shares, price_per_share)
);

CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    cluster_start_date DATE NOT NULL,
    cluster_end_date DATE NOT NULL,
    insider_count INT NOT NULL,
    total_value_usd BIGINT NOT NULL,
    market_cap_usd BIGINT,
    score INT NOT NULL,
    payload JSONB NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    twitter_post_id TEXT,
    UNIQUE (ticker, cluster_end_date)
);

CREATE TABLE ticker_pages (
    ticker TEXT NOT NULL,
    cluster_date DATE NOT NULL,
    payload JSONB NOT NULL,
    score INT NOT NULL,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, cluster_date)
);

CREATE TABLE email_subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    signup_source TEXT,
    loops_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE market_cap_cache (
    ticker TEXT PRIMARY KEY,
    market_cap_usd BIGINT,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clusters_published ON clusters (published_at DESC);
CREATE INDEX idx_clusters_score ON clusters (score DESC);
CREATE INDEX idx_filings_ticker_date ON filings (ticker, trade_date DESC);
