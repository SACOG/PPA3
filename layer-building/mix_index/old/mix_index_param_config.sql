--mix ratios by community type
SELECT
	ComType5,
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD
FROM ilut_combined2020_63_DPS
GROUP BY ComType5

--mix ratios for whole region, EXCLUDE dorms
SELECT
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD
FROM ilut_combined2020_63_DPS

--mix ratios for whole region, INCLUDE dorms
SELECT
	SUM(ENR_K12) / SUM(HH_TOT_P) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_TOT_P) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_TOT_P) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_TOT_P) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_TOT_P) AS EMPFOOD
FROM ilut_combined2020_63_DPS


--mix ratios just for specified community types
SELECT
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD
FROM ilut_combined2020_63_DPS
WHERE ComType5 IN ('Centers and Corridors', 'Established Communities')


