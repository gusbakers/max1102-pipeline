-- PostgreSQL observations for the local pilot; event time depends on producer clocks.
SELECT count(*) AS received_events,
       min(received_at) AS first_received_at,
       max(received_at) AS last_received_at,
       avg(extract(epoch FROM received_at - occurred_at)) AS mean_observed_seconds,
       percentile_cont(0.95) WITHIN GROUP (
           ORDER BY extract(epoch FROM received_at - occurred_at)
       ) AS p95_observed_seconds
FROM week5_stream.events
WHERE received_at >= now() - interval '1 hour';

SELECT reason, count(*) AS rejected_messages
FROM week5_stream.rejections
WHERE rejected_at >= now() - interval '1 hour'
GROUP BY reason ORDER BY reason;

SELECT collection, embedding_model, count(*) AS chunks, max(indexed_at) AS last_indexed_at
FROM week5_knowledge.chunks GROUP BY collection, embedding_model;
