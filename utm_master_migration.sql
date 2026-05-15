-- Expande la tabla `utms` al nuevo maestro UTM.
-- Ejecuta este script en Supabase SQL Editor antes de usar la nueva versión de la app.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'utms' AND column_name = 'utm_sc'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'utms' AND column_name = 'utm_zc'
    ) THEN
        ALTER TABLE utms RENAME COLUMN utm_sc TO utm_zc;
    END IF;
END $$;

ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_id TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_zc TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_name TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_source TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_medium TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_intent TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_business TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_campaign_id TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_asset_id TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_term TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_content TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS owner TEXT;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS utm_created DATE DEFAULT CURRENT_DATE;
ALTER TABLE utms ADD COLUMN IF NOT EXISTS is_seasonal BOOLEAN DEFAULT FALSE;

-- Backfill desde la estructura legacy.
UPDATE utms
SET
    utm_name = COALESCE(utm_name, campaign_name),
    utm_source = COALESCE(utm_source, campaign_source),
    utm_medium = COALESCE(utm_medium, campaign_medium),
    utm_campaign_id = COALESCE(utm_campaign_id, campaign_id),
    utm_term = COALESCE(utm_term, campaign_term),
    utm_content = COALESCE(utm_content, campaign_content),
    utm_created = COALESCE(utm_created, created_at::date);

CREATE UNIQUE INDEX IF NOT EXISTS utms_utm_id_unique_idx
ON utms (utm_id)
WHERE utm_id IS NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_sc_max_30'
    ) THEN
        ALTER TABLE utms DROP CONSTRAINT utms_utm_sc_max_30;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_zc_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_zc_max_30
        CHECK (utm_zc IS NULL OR char_length(utm_zc) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_name_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_name_max_30
        CHECK (utm_name IS NULL OR char_length(utm_name) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_source_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_source_max_30
        CHECK (utm_source IS NULL OR char_length(utm_source) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_medium_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_medium_max_30
        CHECK (utm_medium IS NULL OR char_length(utm_medium) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_intent_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_intent_max_30
        CHECK (utm_intent IS NULL OR char_length(utm_intent) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_business_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_business_max_30
        CHECK (utm_business IS NULL OR char_length(utm_business) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_campaign_id_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_campaign_id_max_30
        CHECK (utm_campaign_id IS NULL OR char_length(utm_campaign_id) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_asset_id_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_asset_id_max_30
        CHECK (utm_asset_id IS NULL OR char_length(utm_asset_id) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_term_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_term_max_30
        CHECK (utm_term IS NULL OR char_length(utm_term) <= 30);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'utms_utm_content_max_30'
    ) THEN
        ALTER TABLE utms
        ADD CONSTRAINT utms_utm_content_max_30
        CHECK (utm_content IS NULL OR char_length(utm_content) <= 30);
    END IF;
END $$;
