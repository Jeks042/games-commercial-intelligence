SELECT 'portfolio_coverage' AS check_name,
 ABS((SELECT COUNT(*) FROM v_portfolio_positioning)-(SELECT COUNT(*) FROM dim_title WHERE cohort='portfolio')) AS violation_count
UNION ALL SELECT 'pair_coverage',ABS((SELECT COUNT(*) FROM v_reference_pair_context)-(SELECT COUNT(*) FROM bridge_title_reference))
UNION ALL SELECT 'metric_coverage',ABS((SELECT COUNT(*) FROM v_direct_peer_benchmark)-4*(SELECT COUNT(*) FROM dim_title WHERE cohort='portfolio'))
UNION ALL SELECT 'reference_metric_coverage',ABS((SELECT COUNT(*) FROM v_reference_metric_context)-4*(SELECT COUNT(*) FROM bridge_title_reference))
UNION ALL SELECT 'benchmark_gate',COUNT(*) FROM v_direct_peer_benchmark
 WHERE (benchmark_status='available_unadjusted_snapshot' AND (expected_reference_count<3 OR valid_reference_count<>expected_reference_count OR direct_peer_median IS NULL))
 OR (benchmark_status<>'available_unadjusted_snapshot' AND (direct_peer_median IS NOT NULL OR target_minus_median IS NOT NULL OR target_to_median_ratio IS NOT NULL OR reference_empirical_percentile IS NOT NULL))
UNION ALL SELECT 'percentile_bounds',COUNT(*) FROM v_direct_peer_benchmark WHERE reference_empirical_percentile NOT BETWEEN 0 AND 100
UNION ALL SELECT 'ratio_semantics',COUNT(*) FROM v_direct_peer_benchmark WHERE (ratio_status<>'available' AND target_to_median_ratio IS NOT NULL) OR (ratio_status='available' AND target_to_median_ratio IS NULL)
UNION ALL SELECT 'pair_context_gate',COUNT(*) FROM v_reference_metric_context WHERE context_status<>'available' AND (target_minus_reference IS NOT NULL OR target_to_reference_ratio IS NOT NULL)
UNION ALL SELECT 'unsupported_classification',COUNT(*) FROM v_portfolio_positioning WHERE overall_performance_classification<>'not_assessed_snapshot_only' OR sustained_activity_status<>'not_established';
