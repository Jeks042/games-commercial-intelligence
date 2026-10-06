PRAGMA foreign_keys = ON;

CREATE TABLE dim_peer_group (
    peer_group TEXT PRIMARY KEY
) STRICT;

CREATE TABLE dim_title (
    app_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    cohort TEXT NOT NULL CHECK (cohort IN ('portfolio','competitor')),
    peer_group TEXT NOT NULL REFERENCES dim_peer_group,
    curated_publisher TEXT,
    curated_developer TEXT,
    curated_release_date TEXT,
    curated_lifecycle_role TEXT,
    source_url TEXT NOT NULL
) STRICT;

CREATE TABLE dim_date (
    date_key TEXT PRIMARY KEY,
    calendar_year INTEGER NOT NULL,
    calendar_month INTEGER NOT NULL,
    calendar_day INTEGER NOT NULL,
    iso_year INTEGER NOT NULL,
    iso_week INTEGER NOT NULL,
    iso_weekday INTEGER NOT NULL CHECK (iso_weekday BETWEEN 1 AND 7),
    week_start_date TEXT NOT NULL
) STRICT;

CREATE TABLE dim_run (
    run_id TEXT PRIMARY KEY,
    source_layer TEXT NOT NULL CHECK (source_layer IN ('steam','steamspy')),
    schema_version INTEGER NOT NULL CHECK (schema_version=2),
    admission_status TEXT NOT NULL CHECK (admission_status='accepted'),
    accepted_at_utc TEXT NOT NULL,
    acceptance_evidence TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT NOT NULL,
    expected_titles INTEGER NOT NULL CHECK (expected_titles>0),
    manifest_path TEXT NOT NULL,
    manifest_canonical_sha256 TEXT NOT NULL,
    observations_sha256 TEXT NOT NULL,
    collector_revision TEXT NOT NULL,
    source_contracts_json TEXT NOT NULL,
    collector_source_hashes_json TEXT NOT NULL,
    review_contract_sha256 TEXT
) STRICT;

CREATE TABLE bridge_title_reference (
    portfolio_app_id INTEGER NOT NULL REFERENCES dim_title,
    reference_app_id INTEGER NOT NULL REFERENCES dim_title,
    peer_role TEXT NOT NULL CHECK (peer_role IN ('direct_peer','category_leader','adjacent_reference','lifecycle_reference')),
    rationale TEXT NOT NULL,
    PRIMARY KEY (portfolio_app_id,reference_app_id),
    CHECK (portfolio_app_id<>reference_app_id)
) STRICT;

CREATE TABLE fact_steam_observation (
    app_id INTEGER NOT NULL REFERENCES dim_title,
    run_id TEXT NOT NULL REFERENCES dim_run,
    observation_timestamp_utc TEXT NOT NULL,
    date_key TEXT NOT NULL REFERENCES dim_date,
    store_name TEXT NOT NULL,
    developer_live TEXT,
    publisher_live TEXT,
    steam_release_date TEXT,
    steam_release_date_text TEXT,
    early_access_genre_flag INTEGER CHECK (early_access_genre_flag IN (0,1)),
    is_free INTEGER NOT NULL CHECK (is_free IN (0,1)),
    coming_soon INTEGER CHECK (coming_soon IN (0,1)),
    currency TEXT CHECK (currency IS NULL OR currency='GBP'),
    price_status TEXT NOT NULL CHECK (price_status IN ('available','unavailable','free')),
    list_price_minor INTEGER CHECK (list_price_minor>=0),
    final_price_minor INTEGER CHECK (final_price_minor>=0),
    discount_percent_reported INTEGER CHECK (discount_percent_reported BETWEEN 0 AND 100),
    total_positive_reviews INTEGER NOT NULL CHECK (total_positive_reviews>=0),
    total_negative_reviews INTEGER NOT NULL CHECK (total_negative_reviews>=0),
    total_reviews INTEGER NOT NULL CHECK (total_reviews>=0),
    review_score_code INTEGER NOT NULL CHECK (review_score_code BETWEEN 0 AND 9),
    review_score_desc TEXT NOT NULL,
    review_query_version TEXT NOT NULL,
    current_players INTEGER NOT NULL CHECK (current_players>=0),
    steam_store_status TEXT NOT NULL CHECK (steam_store_status='ok'),
    steam_reviews_status TEXT NOT NULL CHECK (steam_reviews_status='ok'),
    current_players_status TEXT NOT NULL CHECK (current_players_status='ok'),
    steam_store_retrieved_at_utc TEXT NOT NULL,
    steam_reviews_retrieved_at_utc TEXT NOT NULL,
    current_players_retrieved_at_utc TEXT NOT NULL,
    evidence_class TEXT NOT NULL CHECK (evidence_class='observed'),
    PRIMARY KEY (app_id,run_id),
    UNIQUE (app_id,observation_timestamp_utc),
    CHECK (total_positive_reviews+total_negative_reviews=total_reviews),
    CHECK (final_price_minor IS NULL OR final_price_minor<=list_price_minor),
    CHECK ((price_status='available' AND currency='GBP' AND list_price_minor IS NOT NULL AND final_price_minor IS NOT NULL AND discount_percent_reported IS NOT NULL)
       OR (price_status IN ('unavailable','free') AND list_price_minor IS NULL AND final_price_minor IS NULL AND discount_percent_reported IS NULL))
) STRICT;

CREATE TABLE fact_external_benchmark (
    app_id INTEGER NOT NULL REFERENCES dim_title,
    run_id TEXT NOT NULL REFERENCES dim_run,
    benchmark_source TEXT NOT NULL CHECK (benchmark_source='steamspy'),
    benchmark_timestamp_utc TEXT NOT NULL,
    date_key TEXT NOT NULL REFERENCES dim_date,
    retrieved_at_utc TEXT NOT NULL,
    source_status TEXT NOT NULL CHECK (source_status='ok'),
    owner_band_raw TEXT NOT NULL,
    estimated_owners_lower INTEGER NOT NULL CHECK (estimated_owners_lower>=0),
    estimated_owners_upper INTEGER NOT NULL CHECK (estimated_owners_upper>=estimated_owners_lower),
    owner_estimate_status TEXT NOT NULL CHECK (owner_estimate_status='requires_review'),
    steamspy_peak_ccu_previous_day_reported INTEGER CHECK (steamspy_peak_ccu_previous_day_reported>=0),
    reported_context_status TEXT NOT NULL CHECK (reported_context_status='period_unresolved'),
    steamspy_positive INTEGER CHECK (steamspy_positive>=0),
    steamspy_negative INTEGER CHECK (steamspy_negative>=0),
    average_playtime_forever_minutes INTEGER CHECK (average_playtime_forever_minutes>0),
    average_playtime_2weeks_minutes INTEGER CHECK (average_playtime_2weeks_minutes>0),
    median_playtime_forever_minutes INTEGER CHECK (median_playtime_forever_minutes>0),
    median_playtime_2weeks_minutes INTEGER CHECK (median_playtime_2weeks_minutes>0),
    playtime_status TEXT NOT NULL CHECK (playtime_status IN ('available','partial','unavailable')),
    ownership_evidence_class TEXT NOT NULL CHECK (ownership_evidence_class='estimated'),
    reported_context_evidence_class TEXT NOT NULL CHECK (reported_context_evidence_class='observed'),
    PRIMARY KEY (app_id,run_id,benchmark_source),
    UNIQUE (app_id,benchmark_timestamp_utc,benchmark_source)
) STRICT;

CREATE TABLE dim_metric (
    metric TEXT PRIMARY KEY,
    evidence_class TEXT NOT NULL CHECK (evidence_class IN ('observed','estimated','derived','assumption')),
    grain TEXT NOT NULL,
    source TEXT NOT NULL,
    definition TEXT NOT NULL,
    unit TEXT NOT NULL,
    availability_rule TEXT NOT NULL,
    decision_limit TEXT NOT NULL
) STRICT;

CREATE INDEX ix_steam_title_time ON fact_steam_observation(app_id,observation_timestamp_utc);
CREATE INDEX ix_benchmark_title_time ON fact_external_benchmark(app_id,benchmark_timestamp_utc);
