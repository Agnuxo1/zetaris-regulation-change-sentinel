-- Review queue: assessments whose cited requirement changed in substance.
SELECT assessment_id, policy_area, section_id, owner, facts_removed, facts_added, verdict, successor_url
FROM regsentinel.change_review WHERE verdict LIKE 'REVIEW%' ORDER BY assessment_id;

-- Workload summary.
SELECT verdict, count(*) AS n FROM regsentinel.change_review GROUP BY verdict ORDER BY n DESC;

-- Live provenance: official amendment dates for the sections the register cites.
SELECT v.section_id, v.amendment_date, v.substantive, v.name
FROM (SELECT DISTINCT section_id FROM grants_pg.compliance_register) r
JOIN (SELECT cv.identifier AS section_id, cv.amendment_date, cv.substantive, cv.name
      FROM ecfr_rest.part200_versions LATERAL VIEW explode(content_versions) t AS cv) v
  ON r.section_id = v.section_id
WHERE v.amendment_date = '2024-10-01'
ORDER BY v.section_id;
