SELECT 'fact_run_scope' AS check_name, COUNT(*) AS violations FROM dim_run r
WHERE r.expected_titles<>CASE WHEN r.source_layer='steam'
 THEN (SELECT COUNT(*) FROM fact_steam_observation f WHERE f.run_id=r.run_id)
 ELSE (SELECT COUNT(*) FROM fact_external_benchmark b WHERE b.run_id=r.run_id) END
UNION ALL SELECT 'fact_layer',COUNT(*) FROM (
 SELECT f.run_id FROM fact_steam_observation f JOIN dim_run r USING(run_id) WHERE r.source_layer<>'steam'
 UNION ALL SELECT b.run_id FROM fact_external_benchmark b JOIN dim_run r USING(run_id) WHERE r.source_layer<>'steamspy')
UNION ALL SELECT 'reference_cohort_and_group',COUNT(*) FROM bridge_title_reference b
JOIN dim_title p ON p.app_id=b.portfolio_app_id JOIN dim_title c ON c.app_id=b.reference_app_id
WHERE p.cohort<>'portfolio' OR c.cohort<>'competitor' OR p.peer_group<>c.peer_group
UNION ALL SELECT 'portfolio_reference_coverage',COUNT(*) FROM dim_title t
WHERE t.cohort='portfolio' AND NOT EXISTS(SELECT 1 FROM bridge_title_reference b WHERE b.portfolio_app_id=t.app_id)
UNION ALL SELECT 'reported_discount_arithmetic',COUNT(*) FROM fact_steam_observation
WHERE price_status='available' AND list_price_minor>0
AND ABS(discount_percent_reported-100.0*(list_price_minor-final_price_minor)/list_price_minor)>1
UNION ALL SELECT 'review_ratio_range',COUNT(*) FROM v_steam_metrics
WHERE lifetime_review_positive_percent<0 OR lifetime_review_positive_percent>100
UNION ALL SELECT 'unavailable_playtime_has_values',COUNT(*) FROM fact_external_benchmark
WHERE playtime_status='unavailable' AND (
 average_playtime_forever_minutes IS NOT NULL OR average_playtime_2weeks_minutes IS NOT NULL
 OR median_playtime_forever_minutes IS NOT NULL OR median_playtime_2weeks_minutes IS NOT NULL)
UNION ALL SELECT 'available_playtime_missing_values',COUNT(*) FROM fact_external_benchmark
WHERE playtime_status='available' AND (
 average_playtime_forever_minutes IS NULL OR average_playtime_2weeks_minutes IS NULL
 OR median_playtime_forever_minutes IS NULL OR median_playtime_2weeks_minutes IS NULL)
UNION ALL SELECT 'observation_date',COUNT(*) FROM fact_steam_observation
WHERE date(observation_timestamp_utc)<>date_key
UNION ALL SELECT 'benchmark_date',COUNT(*) FROM fact_external_benchmark
WHERE date(benchmark_timestamp_utc)<>date_key
UNION ALL SELECT 'reference_metric_gate',COUNT(*) FROM v_price_reference
WHERE reference_status<>'available' AND direct_reference_price_index IS NOT NULL
UNION ALL SELECT 'momentum_gate',COUNT(*) FROM v_momentum_readiness
WHERE (player_momentum_status<>'available' AND player_change_3weeks_percent IS NOT NULL)
 OR (review_velocity_status<>'available' AND review_velocity_per_day IS NOT NULL)

UNION ALL SELECT 'partial_playtime_inconsistent',COUNT(*) FROM fact_external_benchmark
WHERE playtime_status='partial' AND (
 (average_playtime_forever_minutes IS NOT NULL)+(average_playtime_2weeks_minutes IS NOT NULL)+
 (median_playtime_forever_minutes IS NOT NULL)+(median_playtime_2weeks_minutes IS NOT NULL)) NOT BETWEEN 1 AND 3;
