CREATE VIEW v_steam_metrics AS
WITH measures AS (
 SELECT f.*, t.title, t.cohort, t.peer_group, t.curated_lifecycle_role,
        t.curated_release_date, r.review_contract_sha256,
        date(f.steam_store_retrieved_at_utc) AS price_date_key,
        date(f.steam_reviews_retrieved_at_utc) AS review_date_key,
        date(f.current_players_retrieved_at_utc) AS player_date_key,
        CAST(julianday(date(f.steam_store_retrieved_at_utc))-julianday(f.steam_release_date) AS INTEGER) AS title_age_days,
        CASE WHEN f.price_status='available' THEN f.list_price_minor/100.0 END AS list_price_gbp,
        CASE WHEN f.price_status='available' THEN f.final_price_minor/100.0 END AS final_price_gbp,
        CASE WHEN f.price_status='available' AND f.list_price_minor>0
             THEN ROUND(100.0*(f.list_price_minor-f.final_price_minor)/f.list_price_minor,4) END AS discount_depth_percent,
        CASE WHEN f.total_reviews>0
             THEN ROUND(100.0*f.total_positive_reviews/f.total_reviews,4) END AS lifetime_review_positive_percent
 FROM fact_steam_observation f JOIN dim_title t USING(app_id) JOIN dim_run r USING(run_id)
)
SELECT m.*,
       CASE WHEN early_access_genre_flag=1 THEN 'early_access'
            WHEN title_age_days IS NULL THEN 'unknown'
            WHEN title_age_days<0 THEN 'pre_release'
            WHEN title_age_days<90 THEN 'launch'
            WHEN title_age_days<365 THEN 'early_lifecycle'
            WHEN title_age_days<1095 THEN 'established'
            ELSE 'back_catalogue' END AS analytical_lifecycle,
       'derived' AS calculated_evidence_class
FROM measures m;

CREATE VIEW v_latest_steam_metrics AS
SELECT * FROM (
 SELECT m.*, ROW_NUMBER() OVER(PARTITION BY app_id ORDER BY observation_timestamp_utc DESC,run_id DESC) AS observation_rank
 FROM v_steam_metrics m
) WHERE observation_rank=1;

-- Only direct peers with current same-day GBP quotes enter the price reference.
-- Require at least three references and complete configured direct-peer coverage.
CREATE VIEW v_price_reference AS
WITH expected AS (
 SELECT portfolio_app_id, COUNT(*) AS expected_direct_reference_count
 FROM bridge_title_reference WHERE peer_role='direct_peer' GROUP BY portfolio_app_id
), prices AS (
 SELECT b.portfolio_app_id, p.final_price_minor,
        ROW_NUMBER() OVER(PARTITION BY b.portfolio_app_id ORDER BY p.final_price_minor,p.app_id) AS price_rank,
        COUNT(*) OVER(PARTITION BY b.portfolio_app_id) AS reference_count
 FROM bridge_title_reference b
 JOIN v_latest_steam_metrics p ON p.app_id=b.reference_app_id
 JOIN v_latest_steam_metrics target ON target.app_id=b.portfolio_app_id
 WHERE b.peer_role='direct_peer' AND p.price_status='available'
   AND p.currency='GBP' AND date(p.steam_store_retrieved_at_utc)=date(target.steam_store_retrieved_at_utc)
), medians AS (
 SELECT portfolio_app_id, MAX(reference_count) AS valid_direct_reference_count,
        AVG(final_price_minor) AS median_price_minor
 FROM prices WHERE price_rank IN ((reference_count+1)/2,(reference_count+2)/2)
 GROUP BY portfolio_app_id
)
SELECT t.app_id,t.title,t.peer_group,t.run_id,t.steam_store_retrieved_at_utc,
       t.final_price_gbp,COALESCE(e.expected_direct_reference_count,0) AS expected_direct_reference_count,
       COALESCE(m.valid_direct_reference_count,0) AS valid_direct_reference_count,
       CASE WHEN m.valid_direct_reference_count>=3 AND m.valid_direct_reference_count=e.expected_direct_reference_count
            THEN m.median_price_minor/100.0 END AS direct_reference_median_price_gbp,
       CASE WHEN m.valid_direct_reference_count>=3 AND m.valid_direct_reference_count=e.expected_direct_reference_count
                 AND m.median_price_minor>0 AND t.price_status='available'
            THEN ROUND(1.0*t.final_price_minor/m.median_price_minor,4) END AS direct_reference_price_index,
       CASE WHEN COALESCE(e.expected_direct_reference_count,0)<3 THEN 'insufficient_reference_count'
            WHEN COALESCE(m.valid_direct_reference_count,0)<>e.expected_direct_reference_count THEN 'incomplete_same_day_coverage'
            WHEN t.price_status<>'available' THEN 'title_price_unavailable'
            WHEN m.median_price_minor=0 THEN 'zero_reference_median'
            ELSE 'available' END AS reference_status,
       'derived' AS evidence_class
FROM v_latest_steam_metrics t
LEFT JOIN expected e ON e.portfolio_app_id=t.app_id
LEFT JOIN medians m ON m.portfolio_app_id=t.app_id
WHERE t.cohort='portfolio';

CREATE VIEW v_weekly_comparable_pulse AS
WITH eligible AS (
 SELECT f.*, d.week_start_date,r.review_contract_sha256,
        ROW_NUMBER() OVER(
            PARTITION BY f.app_id,d.week_start_date,r.review_contract_sha256
            ORDER BY ABS(CAST(strftime('%H',f.current_players_retrieved_at_utc) AS INTEGER)*60+
                         CAST(strftime('%M',f.current_players_retrieved_at_utc) AS INTEGER)-375),
                     f.current_players_retrieved_at_utc DESC,f.run_id DESC
        ) AS slot_rank
 FROM fact_steam_observation f
 JOIN dim_date d ON d.date_key=date(f.current_players_retrieved_at_utc)
 JOIN dim_run r USING(run_id)
 WHERE strftime('%w',f.current_players_retrieved_at_utc)='1'
   AND CAST(strftime('%H',f.current_players_retrieved_at_utc) AS INTEGER)*60+
       CAST(strftime('%M',f.current_players_retrieved_at_utc) AS INTEGER) BETWEEN 330 AND 420
)
SELECT * FROM eligible WHERE slot_rank=1;

CREATE VIEW v_momentum_readiness AS
WITH ranked AS (
 SELECT w.*,LEAD(total_reviews) OVER(PARTITION BY w.app_id,w.review_contract_sha256 ORDER BY w.week_start_date DESC) AS previous_review_count,ROW_NUMBER() OVER(
     PARTITION BY w.app_id,w.review_contract_sha256 ORDER BY w.week_start_date DESC) AS period_rank
 FROM v_weekly_comparable_pulse w
), series AS (
 SELECT app_id,review_contract_sha256,COUNT(*) AS comparable_week_count,
        MIN(CASE WHEN period_rank<=4 THEN week_start_date END) AS first_week,
        MAX(week_start_date) AS last_week,
        MAX(CASE WHEN period_rank=1 THEN current_players END) AS last_players,
        MAX(CASE WHEN period_rank=4 THEN current_players END) AS first_players,
        MAX(CASE WHEN period_rank=1 THEN total_reviews END) AS last_reviews,
        MAX(CASE WHEN period_rank=4 THEN total_reviews END) AS first_reviews,
        MAX(CASE WHEN period_rank=1 THEN steam_reviews_retrieved_at_utc END) AS last_review_at,
        MAX(CASE WHEN period_rank=4 THEN steam_reviews_retrieved_at_utc END) AS first_review_at,
        MAX(CASE WHEN period_rank=1 THEN current_players_retrieved_at_utc END) AS last_player_at,
        MAX(CASE WHEN period_rank<=3 AND total_reviews<previous_review_count THEN 1 ELSE 0 END) AS review_revisions
 FROM ranked GROUP BY app_id,review_contract_sha256
), readiness AS (
 SELECT t.app_id,t.title,t.run_id,t.review_query_version,t.review_contract_sha256,
        t.current_players_retrieved_at_utc AS latest_observation_at_utc,
        COALESCE(s.comparable_week_count,0) AS comparable_week_count,
        s.first_week,s.last_week,s.first_players,s.last_players,s.first_reviews,s.last_reviews,
        s.first_review_at,s.last_review_at,s.last_player_at,s.review_revisions,
        CASE WHEN COALESCE(s.comparable_week_count,0)<4 THEN 'insufficient_comparable_history'
             WHEN julianday(s.last_week)-julianday(s.first_week)<>21 THEN 'nonconsecutive_periods'
             WHEN julianday(date(t.current_players_retrieved_at_utc))-julianday(s.last_week)>14 THEN 'stale_history'
             ELSE 'available' END AS history_status
 FROM v_latest_steam_metrics t
 LEFT JOIN series s ON s.app_id=t.app_id AND s.review_contract_sha256=t.review_contract_sha256
)
SELECT app_id,title,run_id,review_query_version,review_contract_sha256,latest_observation_at_utc,
       comparable_week_count,last_player_at AS latest_comparable_player_at_utc,
       CASE WHEN history_status='available' AND first_players>0
            THEN ROUND(100.0*(last_players-first_players)/first_players,4) END AS player_change_3weeks_percent,
       CASE WHEN history_status='available' AND first_players=0 THEN 'zero_baseline' ELSE history_status END AS player_momentum_status,
       CASE WHEN history_status='available' AND review_revisions=0
            THEN ROUND(1.0*(last_reviews-first_reviews)/(julianday(last_review_at)-julianday(first_review_at)),4) END AS review_velocity_per_day,
       CASE WHEN history_status='available' AND review_revisions=1 THEN 'source_revision'
            ELSE history_status END AS review_velocity_status,
       4 AS minimum_comparable_weeks,'derived' AS evidence_class
FROM readiness;
