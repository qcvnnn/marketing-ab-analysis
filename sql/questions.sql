-- Each question uses the latest SUCCESSFUL input version; failed loads are excluded.

-- 1. How do conversion rates differ? JOIN + GROUP BY in the underlying view.
SELECT * FROM campaign.v_group_metrics
WHERE batch_id=(SELECT max(batch_id) FROM campaign.loads WHERE status='success')
ORDER BY test_group;

-- 2. What fraction of users and conversions belongs to each group? SUM OVER.
SELECT test_group,users,conversions,
 round(100.0*users/sum(users) OVER (),2) AS user_share_pct,
 round(100.0*conversions/NULLIF(sum(conversions) OVER (),0),2) AS conversion_share_pct
FROM campaign.v_group_metrics
WHERE batch_id=(SELECT max(batch_id) FROM campaign.loads WHERE status='success');

-- 3. Which exposure buckets have the largest observed conversion rate? DENSE_RANK.
-- Descriptive only: do not use this ranking as a causal targeting recommendation.
SELECT test_group,exposure_bucket,users,conversion_rate,
 dense_rank() OVER (PARTITION BY test_group ORDER BY conversion_rate DESC) AS observed_rank
FROM campaign.v_exposure_summary
WHERE batch_id=(SELECT max(batch_id) FROM campaign.loads WHERE status='success')
ORDER BY test_group,observed_rank;

-- 4. Which exposure buckets contain most of the users? Explicit cumulative window.
SELECT test_group,exposure_bucket,users,
 sum(users) OVER (PARTITION BY test_group ORDER BY exposure_bucket
   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_users
FROM campaign.v_exposure_summary
WHERE batch_id=(SELECT max(batch_id) FROM campaign.loads WHERE status='success')
ORDER BY test_group,exposure_bucket;

-- 5. Differences between adjacent hour categories. LAG is not a time-series claim:
-- most_ads_hour is the user's peak-exposure hour, not an event timestamp.
WITH hourly AS (
 SELECT test_group,most_ads_hour,count(*) AS users,avg(converted::integer) AS rate
 FROM campaign.users WHERE batch_id=(SELECT max(batch_id) FROM campaign.loads WHERE status='success')
 GROUP BY test_group,most_ads_hour
)
SELECT *,rate-lag(rate) OVER (PARTITION BY test_group ORDER BY most_ads_hour) AS adjacent_hour_difference
FROM hourly ORDER BY test_group,most_ads_hour;

-- 6. Are the SQL group totals consistent with the user table?
SELECT b.batch_id,b.row_count,count(u.user_id) AS stored_rows,
 count(DISTINCT u.user_id) AS unique_users
FROM campaign.loads b LEFT JOIN campaign.users u USING (batch_id)
GROUP BY b.batch_id,b.row_count ORDER BY b.batch_id;
