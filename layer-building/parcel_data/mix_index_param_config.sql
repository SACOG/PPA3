--mix ratios by community type
SELECT
	ComType5,
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD,
	SUM(CASE WHEN LU = 'Park and/or Open Space' 
		THEN CAST(GISAc AS FLOAT) ELSE 0 END) / SUM(HH_hh) AS PARK_AC
FROM ilut_combined2020_63_DPS
GROUP BY ComType5

--mix ratios for whole region
SELECT
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD,
	SUM(CASE WHEN LU = 'Park and/or Open Space' 
		THEN CAST(GISAc AS FLOAT) ELSE 0 END) / SUM(HH_hh) AS PARK_AC
FROM ilut_combined2020_63_DPS


--mix ratios just for specified community types
SELECT
	SUM(ENR_K12) / SUM(HH_hh) AS ENR_K12,
	SUM(EMPRET) / SUM(HH_hh) AS EMPRET,
	SUM(EMPTOT) / SUM(HH_hh) AS EMPTOT,
	SUM(EMPSVC) / SUM(HH_hh) AS EMPSVC,
	SUM(EMPFOOD) / SUM(HH_hh) AS EMPFOOD,
	SUM(CASE WHEN LU = 'Park and/or Open Space' 
		THEN CAST(GISAc AS FLOAT) ELSE 0 END) / SUM(HH_hh) AS PARK_AC
FROM ilut_combined2020_63_DPS
WHERE ComType5 IN ('Centers and Corridors', 'Established Communities')


