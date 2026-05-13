ALTER TABLE email_subscribers
    ADD COLUMN IF NOT EXISTS signup_ticker TEXT,
    ADD COLUMN IF NOT EXISTS signup_campaign TEXT,
    ADD COLUMN IF NOT EXISTS signup_variant TEXT,
    ADD COLUMN IF NOT EXISTS signup_referrer TEXT;

CREATE INDEX IF NOT EXISTS idx_email_subscribers_source_created
    ON email_subscribers (signup_source, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_subscribers_campaign_created
    ON email_subscribers (signup_campaign, created_at DESC);
