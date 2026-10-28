-- Modal-aware v2 candidate, developed after inspecting known errors.
-- Regulation Change Sentinel: one federated Zetaris view over three live sources.
--   grants_pg.compliance_register   PostgreSQL datasource (organisation's assessments)
--   ecfr_files.paragraphs           CSV file store (eCFR paragraph snapshots, both versions)
--   ecfr_rest.part200_versions      live eCFR versioner REST API (official amendment dates)
-- Every decision below is computed inside Zetaris; the agent only reads the result.
-- Fixed a priori (not tuned on labels): successor distance cut-off 0.60.
CREATE SCHEMASTORE VIEW change_review_modal_v2 WITH CONTAINER regsentinel AS
WITH reg AS (
  SELECT assessment_id, policy_area, section_id, cited_ordinal, cited_text,
         CAST(cited_version AS STRING) AS cited_version, owner, source_url AS cited_url
  FROM grants_pg.compliance_register
), newp AS (
  SELECT section_id, CAST(ordinal AS INT) AS ordinal, paragraph_text, source_url
  FROM ecfr_files.paragraphs WHERE version_date = '2024-10-01'
), amend AS (
  SELECT cv.identifier AS section_id, max(cv.amendment_date) AS amendment_date,
         max(CAST(cv.substantive AS STRING)) AS substantive
  FROM ecfr_rest.part200_versions LATERAL VIEW explode(content_versions) t AS cv
  WHERE cv.amendment_date > '2024-09-30' AND cv.amendment_date <= '2024-10-01'
  GROUP BY cv.identifier
), cand AS (
  SELECT r.assessment_id, n.ordinal AS successor_ordinal, n.paragraph_text AS successor_text,
         n.source_url AS successor_url,
         levenshtein(lower(r.cited_text), lower(n.paragraph_text))
           / greatest(length(r.cited_text), length(n.paragraph_text)) AS distance
  FROM reg r JOIN newp n ON r.section_id = n.section_id
), best AS (
  SELECT * FROM (
    SELECT c.*, row_number() OVER (PARTITION BY assessment_id ORDER BY distance, successor_ordinal) AS rk
    FROM cand c) WHERE rk = 1
), facts AS (
  SELECT r.*, b.successor_ordinal, b.successor_text, b.successor_url, b.distance,
         a.amendment_date, a.substantive,
         array_sort(array_distinct(concat(
           regexp_extract_all(regexp_replace(lower(r.cited_text), '(§+ ?[0-9.]+|part [0-9]+|\\([a-z0-9]+\\))', ' '), '([0-9][0-9,.]*[0-9]|[0-9])', 1),
           regexp_extract_all(lower(r.cited_text), '\\b(must not|may not|must|may|will|can|should|shall|unallowable|allowable|prior written approval|prior approval|required|prohibited|percent|calendar days|months|years)\\b', 1)))) AS facts_before,
         array_sort(array_distinct(concat(
           regexp_extract_all(regexp_replace(lower(coalesce(b.successor_text, '')), '(§+ ?[0-9.]+|part [0-9]+|\\([a-z0-9]+\\))', ' '), '([0-9][0-9,.]*[0-9]|[0-9])', 1),
           regexp_extract_all(lower(coalesce(b.successor_text, '')), '\\b(must not|may not|must|may|will|can|should|shall|unallowable|allowable|prior written approval|prior approval|required|prohibited|percent|calendar days|months|years)\\b', 1)))) AS facts_after
  FROM reg r LEFT JOIN best b ON r.assessment_id = b.assessment_id
  LEFT JOIN amend a ON r.section_id = a.section_id
)
SELECT assessment_id, policy_area, section_id, owner, cited_version, amendment_date, substantive,
       cited_text, cited_url, successor_ordinal, successor_text, successor_url,
       round(distance, 4) AS distance, facts_before, facts_after,
       array_except(facts_before, facts_after) AS facts_removed,
       array_except(facts_after, facts_before) AS facts_added,
       CASE WHEN distance = 0 THEN 'UNCHANGED'
            WHEN distance IS NULL OR distance > 0.60 THEN 'REVIEW_NOT_FOUND'
            WHEN size(array_except(facts_before, facts_after)) > 0
              OR size(array_except(facts_after, facts_before)) > 0 THEN 'REVIEW_MATERIAL'
            ELSE 'EDITORIAL_ONLY' END AS verdict
FROM facts
