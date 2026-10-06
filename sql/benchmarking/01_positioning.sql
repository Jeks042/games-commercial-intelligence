-- Comparisons are snapshot context, not lifecycle-adjusted performance estimates.
CREATE VIEW v_reference_pair_context AS
SELECT b.portfolio_app_id, t.title AS portfolio_title, b.reference_app_id,
       p.title AS reference_title, b.peer_role, b.rationale,
       t.run_id AS portfolio_run_id, p.run_id AS reference_run_id,
       t.peer_group, t.analytical_lifecycle AS portfolio_lifecycle,
       p.analytical_lifecycle AS reference_lifecycle,
       t.title_age_days AS portfolio_age_days, p.title_age_days AS reference_age_days,
       CASE WHEN t.analytical_lifecycle IN ('unknown','pre_release') OR p.analytical_lifecycle IN ('unknown','pre_release')
            THEN 'unresolved' WHEN t.analytical_lifecycle=p.analytical_lifecycle
            THEN 'same_bucket_unadjusted' ELSE 'different_lifecycle_unadjusted' END AS lifecycle_context,
       t.final_price_gbp AS portfolio_price_gbp, p.final_price_gbp AS reference_price_gbp,
       t.discount_depth_percent AS portfolio_discount_percent, p.discount_depth_percent AS reference_discount_percent,
       t.total_reviews AS portfolio_review_count, p.total_reviews AS reference_review_count,
       t.lifetime_review_positive_percent AS portfolio_positive_percent,
       p.lifetime_review_positive_percent AS reference_positive_percent,
       t.current_players AS portfolio_current_players, p.current_players AS reference_current_players,
       t.steam_store_retrieved_at_utc AS portfolio_price_at_utc, p.steam_store_retrieved_at_utc AS reference_price_at_utc,
       t.steam_reviews_retrieved_at_utc AS portfolio_reviews_at_utc, p.steam_reviews_retrieved_at_utc AS reference_reviews_at_utc,
       t.current_players_retrieved_at_utc AS portfolio_players_at_utc, p.current_players_retrieved_at_utc AS reference_players_at_utc,
       CASE WHEN t.price_status<>'available' OR p.price_status<>'available' OR t.currency<>'GBP' OR p.currency<>'GBP'
            THEN 'price_unavailable' WHEN t.price_date_key<>p.price_date_key
            OR ABS(julianday(t.steam_store_retrieved_at_utc)-julianday(p.steam_store_retrieved_at_utc))*86400>300
            THEN 'different_collection_period' ELSE 'available' END AS price_context_status,
       CASE WHEN t.review_contract_sha256<>p.review_contract_sha256 THEN 'different_review_contract'
            WHEN t.review_date_key<>p.review_date_key
            OR ABS(julianday(t.steam_reviews_retrieved_at_utc)-julianday(p.steam_reviews_retrieved_at_utc))*86400>300
            THEN 'different_collection_period' ELSE 'available' END AS review_volume_context_status,
       CASE WHEN t.review_contract_sha256<>p.review_contract_sha256 THEN 'different_review_contract'
            WHEN t.review_date_key<>p.review_date_key
            OR ABS(julianday(t.steam_reviews_retrieved_at_utc)-julianday(p.steam_reviews_retrieved_at_utc))*86400>300
            THEN 'different_collection_period' WHEN t.total_reviews<100 OR p.total_reviews<100
            THEN 'insufficient_review_count' ELSE 'available' END AS positivity_context_status,
       CASE WHEN t.player_date_key<>p.player_date_key
            OR ABS(julianday(t.current_players_retrieved_at_utc)-julianday(p.current_players_retrieved_at_utc))*86400>300
            THEN 'different_collection_period' ELSE 'available' END AS player_context_status,
       'derived' AS evidence_class
FROM bridge_title_reference b
JOIN v_latest_steam_metrics t ON t.app_id=b.portfolio_app_id
JOIN v_latest_steam_metrics p ON p.app_id=b.reference_app_id;

CREATE VIEW v_reference_metric_context AS
WITH values_long AS (
 SELECT portfolio_app_id,reference_app_id,peer_role,'final_price_gbp' AS metric,
        portfolio_price_gbp AS target_value,reference_price_gbp AS reference_value,
        price_context_status AS context_status FROM v_reference_pair_context
 UNION ALL
 SELECT portfolio_app_id,reference_app_id,peer_role,'lifetime_review_positive_percent',
        portfolio_positive_percent,reference_positive_percent,positivity_context_status FROM v_reference_pair_context
 UNION ALL
 SELECT portfolio_app_id,reference_app_id,peer_role,'lifetime_review_count',
        portfolio_review_count,reference_review_count,review_volume_context_status FROM v_reference_pair_context
 UNION ALL
 SELECT portfolio_app_id,reference_app_id,peer_role,'current_players',
        portfolio_current_players,reference_current_players,player_context_status FROM v_reference_pair_context
)
SELECT v.*, p.portfolio_title,p.reference_title,p.portfolio_lifecycle,p.reference_lifecycle,p.lifecycle_context,
       p.portfolio_run_id,p.reference_run_id,
       CASE v.metric WHEN 'final_price_gbp' THEN p.portfolio_price_at_utc WHEN 'current_players' THEN p.portfolio_players_at_utc ELSE p.portfolio_reviews_at_utc END AS target_at_utc,
       CASE v.metric WHEN 'final_price_gbp' THEN p.reference_price_at_utc WHEN 'current_players' THEN p.reference_players_at_utc ELSE p.reference_reviews_at_utc END AS reference_at_utc,
       CASE WHEN context_status='available' THEN ROUND(target_value-reference_value,4) END AS target_minus_reference,
       CASE WHEN context_status='available' AND reference_value>0 AND metric<>'lifetime_review_positive_percent'
            THEN ROUND(1.0*target_value/reference_value,4) END AS target_to_reference_ratio,
       CASE WHEN context_status<>'available' THEN context_status
            WHEN metric='lifetime_review_positive_percent' THEN 'not_applicable_use_percentage_points'
            WHEN reference_value=0 THEN 'zero_reference_value' ELSE 'available' END AS ratio_status,
       'individual_reference_context_only' AS interpretation, 'derived' AS evidence_class
FROM values_long v JOIN v_reference_pair_context p USING(portfolio_app_id,reference_app_id,peer_role);

CREATE VIEW v_direct_peer_benchmark AS
WITH metric_list(metric) AS (VALUES ('final_price_gbp'),('lifetime_review_positive_percent'),('lifetime_review_count'),('current_players')),
expected AS (
 SELECT t.app_id,t.title,t.peer_group,t.analytical_lifecycle,t.title_age_days,t.run_id,m.metric,
        CASE m.metric WHEN 'final_price_gbp' THEN t.steam_store_retrieved_at_utc WHEN 'current_players' THEN t.current_players_retrieved_at_utc ELSE t.steam_reviews_retrieved_at_utc END AS target_at_utc,
        CASE m.metric WHEN 'final_price_gbp' THEN t.final_price_gbp
             WHEN 'lifetime_review_positive_percent' THEN t.lifetime_review_positive_percent
             WHEN 'lifetime_review_count' THEN t.total_reviews ELSE t.current_players END AS target_value,
        (SELECT COUNT(*) FROM bridge_title_reference b WHERE b.portfolio_app_id=t.app_id AND b.peer_role='direct_peer') AS expected_reference_count
 FROM v_latest_steam_metrics t CROSS JOIN metric_list m WHERE t.cohort='portfolio'
), valid AS (
 SELECT v.*, ROW_NUMBER() OVER(PARTITION BY portfolio_app_id,metric ORDER BY reference_value,reference_app_id) AS value_rank,
        COUNT(*) OVER(PARTITION BY portfolio_app_id,metric) AS valid_reference_count
 FROM v_reference_metric_context v WHERE peer_role='direct_peer' AND context_status='available'
), medians AS (
 SELECT portfolio_app_id,metric,MAX(valid_reference_count) AS valid_reference_count,AVG(reference_value) AS median_value
 FROM valid WHERE value_rank IN ((valid_reference_count+1)/2,(valid_reference_count+2)/2)
 GROUP BY portfolio_app_id,metric
), ranks AS (
 SELECT portfolio_app_id,metric,MIN(reference_at_utc) AS first_reference_at_utc,MAX(reference_at_utc) AS last_reference_at_utc,
        SUM(CASE WHEN reference_value<target_value THEN 1.0 WHEN reference_value=target_value THEN 0.5 ELSE 0 END) AS midpoint_rank
 FROM valid GROUP BY portfolio_app_id,metric
), lifecycle AS (
 SELECT portfolio_app_id,COUNT(*) AS direct_peer_count,
        SUM(CASE WHEN lifecycle_context='same_bucket_unadjusted' THEN 1 ELSE 0 END) AS same_lifecycle_reference_count,
        SUM(CASE WHEN lifecycle_context='unresolved' THEN 1 ELSE 0 END) AS unresolved_lifecycle_reference_count,
        MIN(reference_age_days) AS minimum_reference_age_days,MAX(reference_age_days) AS maximum_reference_age_days
 FROM v_reference_pair_context WHERE peer_role='direct_peer' GROUP BY portfolio_app_id
), gated AS (
 SELECT e.*,COALESCE(m.valid_reference_count,0) AS valid_reference_count,m.median_value,r.midpoint_rank,r.first_reference_at_utc,r.last_reference_at_utc,
        COALESCE(l.same_lifecycle_reference_count,0) AS same_lifecycle_reference_count,
        l.minimum_reference_age_days,l.maximum_reference_age_days,
        CASE WHEN COALESCE(l.unresolved_lifecycle_reference_count,0)>0 OR e.analytical_lifecycle IN ('unknown','pre_release') THEN 'unresolved'
             WHEN l.same_lifecycle_reference_count=e.expected_reference_count AND e.expected_reference_count>0 THEN 'same_bucket_unadjusted'
             ELSE 'mixed_lifecycle_unadjusted' END AS lifecycle_context,
        CASE WHEN e.expected_reference_count<3 THEN 'insufficient_direct_peers'
             WHEN COALESCE(m.valid_reference_count,0)<>e.expected_reference_count THEN 'incomplete_comparable_coverage'
             ELSE 'available_unadjusted_snapshot' END AS benchmark_status
 FROM expected e LEFT JOIN medians m ON m.portfolio_app_id=e.app_id AND m.metric=e.metric
 LEFT JOIN ranks r ON r.portfolio_app_id=e.app_id AND r.metric=e.metric
 LEFT JOIN lifecycle l ON l.portfolio_app_id=e.app_id
)
SELECT app_id,title,peer_group,analytical_lifecycle,title_age_days,run_id,metric,target_value,target_at_utc,first_reference_at_utc,last_reference_at_utc,
       expected_reference_count,valid_reference_count,
       CASE WHEN benchmark_status='available_unadjusted_snapshot' THEN ROUND(median_value,4) END AS direct_peer_median,
       CASE WHEN benchmark_status='available_unadjusted_snapshot' THEN ROUND(target_value-median_value,4) END AS target_minus_median,
       CASE WHEN benchmark_status='available_unadjusted_snapshot' AND median_value>0 AND metric<>'lifetime_review_positive_percent'
            THEN ROUND(1.0*target_value/median_value,4) END AS target_to_median_ratio,
       CASE WHEN benchmark_status<>'available_unadjusted_snapshot' THEN benchmark_status
            WHEN metric='lifetime_review_positive_percent' THEN 'not_applicable_use_percentage_points'
            WHEN median_value=0 THEN 'zero_reference_median' ELSE 'available' END AS ratio_status,
       CASE WHEN benchmark_status='available_unadjusted_snapshot' THEN ROUND(100.0*midpoint_rank/valid_reference_count,4) END AS reference_empirical_percentile,
       benchmark_status,lifecycle_context,same_lifecycle_reference_count,minimum_reference_age_days,maximum_reference_age_days,
       'direct_peer' AS peer_role,'unadjusted_configured_direct_peers_only' AS comparison_basis,'derived' AS evidence_class
FROM gated;

CREATE VIEW v_portfolio_positioning AS
SELECT t.app_id,t.title,t.peer_group,t.run_id,t.steam_store_retrieved_at_utc,t.steam_reviews_retrieved_at_utc,t.current_players_retrieved_at_utc,
       t.analytical_lifecycle,t.title_age_days,t.early_access_genre_flag,
       t.list_price_gbp,t.final_price_gbp,t.discount_depth_percent,t.total_reviews,
       t.lifetime_review_positive_percent,t.current_players,
       (SELECT COUNT(*) FROM bridge_title_reference b WHERE b.portfolio_app_id=t.app_id AND b.peer_role='direct_peer') AS direct_peer_count,
       (SELECT COUNT(*) FROM bridge_title_reference b WHERE b.portfolio_app_id=t.app_id AND b.peer_role<>'direct_peer') AS context_reference_count,
       m.player_change_3weeks_percent,m.player_momentum_status,m.review_velocity_per_day,m.review_velocity_status,
       'unavailable_playtime' AS engagement_depth_status,'excluded_pending_suitability_review' AS ownership_analysis_status,
       'not_established' AS sustained_activity_status,'not_assessed_snapshot_only' AS overall_performance_classification,
       'observed_and_derived' AS evidence_class
FROM v_latest_steam_metrics t JOIN v_momentum_readiness m USING(app_id)
WHERE t.cohort='portfolio';

CREATE VIEW v_lifecycle_coverage AS
SELECT cohort,analytical_lifecycle,COUNT(*) AS title_count,
       COUNT(DISTINCT peer_group) AS represented_peer_groups,
       MIN(title_age_days) AS minimum_title_age_days,MAX(title_age_days) AS maximum_title_age_days,
       'inventory_only_no_cross_genre_performance_ranking' AS interpretation
FROM v_latest_steam_metrics GROUP BY cohort,analytical_lifecycle;
