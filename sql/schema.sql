CREATE SCHEMA IF NOT EXISTS campaign;
CREATE TABLE IF NOT EXISTS campaign.loads (
 batch_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_sha256 text NOT NULL UNIQUE CHECK (length(source_sha256)=64),
 source_name text NOT NULL,
 status text NOT NULL CHECK (status IN ('loading','success','failed')),
 started_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at timestamptz,
 row_count integer CHECK (row_count>=0),
 error_class text
);
CREATE TABLE IF NOT EXISTS campaign.users (
 batch_id bigint NOT NULL REFERENCES campaign.loads,
 user_id bigint NOT NULL CHECK (user_id>0),
 test_group text NOT NULL CHECK (test_group IN ('ad','psa')),
 converted boolean NOT NULL,
 total_ads integer NOT NULL CHECK (total_ads>=0),
 most_ads_day text NOT NULL CHECK (most_ads_day IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')),
 most_ads_hour integer NOT NULL CHECK (most_ads_hour BETWEEN 0 AND 23),
 PRIMARY KEY (batch_id,user_id)
);

CREATE OR REPLACE VIEW campaign.v_group_metrics AS
SELECT u.batch_id,u.test_group,count(*) AS users,
 sum(u.converted::integer) AS conversions,avg(u.converted::integer) AS conversion_rate,
 avg(u.total_ads) AS mean_exposure
FROM campaign.users u JOIN campaign.loads b USING (batch_id)
WHERE b.status='success' GROUP BY u.batch_id,u.test_group;

-- These are exposure summaries, not pre-treatment targeting segments.
CREATE OR REPLACE VIEW campaign.v_exposure_summary AS
WITH prepared AS (
 SELECT u.*, CASE WHEN total_ads<10 THEN '01: 0–9'
                  WHEN total_ads<50 THEN '02: 10–49'
                  WHEN total_ads<100 THEN '03: 50–99' ELSE '04: 100+' END AS exposure_bucket
 FROM campaign.users u JOIN campaign.loads b USING (batch_id) WHERE b.status='success'
)
SELECT batch_id,test_group,exposure_bucket,count(*) AS users,
 sum(converted::integer) AS conversions,avg(converted::integer) AS conversion_rate
FROM prepared GROUP BY batch_id,test_group,exposure_bucket;
