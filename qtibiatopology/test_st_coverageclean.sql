-- Test query to verify ST_CoverageClean is available in PostGIS
-- Run this in your PostgreSQL database to check the function

-- 1. Check if the function exists
SELECT
    n.nspname as schema,
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments,
    pg_get_function_result(p.oid) as return_type
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname ILIKE '%coverageclean%';

-- 2. Simple test with two adjacent polygons using ST_CoverageClean as a WINDOW FUNCTION
WITH test_coverage AS (
    SELECT 1 as id, ST_GeomFromText('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))') as geom
    UNION ALL
    SELECT 2 as id, ST_GeomFromText('POLYGON((10 0, 20 0, 20 10, 10 10, 10 0))') as geom
)
SELECT
    id,
    ST_AsText(
        ST_CoverageClean(geom, 0.01, -1, 'MERGE_LONGEST_BORDER') OVER ()
    ) as cleaned_geom
FROM test_coverage
ORDER BY id;
