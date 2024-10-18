/*
Name: PPA2_NPMRDS_metrics.sql
Purpose: Get data for each TMC for PPA 2.0 calcs:
	TMC code,
	Road name,
	Road number,
	F_System,
	off-peak free-flow speed (85th pctl for fwys; for arterials is 60th pctl to account for signal delay, 8pm-6am, all days),
	80th percentile TT:
		Weekdays 6am-10am
		Weekdays 10am-4pm
		Weekdays 4pm-8pm
		Weekends 6am-8pm,
	50th percentile TT:
		Weekdays 6am-10am
		Weekdays 10am-4pm
		Weekdays 4pm-8pm
		Weekends 6am-8pm,
	LOTTRs (80th/50th):
		Weekdays 6am-10am
		Weekdays 10am-4pm
		Weekdays 4pm-8pm
		Weekends 6am-8pm,
	Worst/highest LOTTR,
	Period of worst/highest LOTTR,
	Avg speed during worst 4 weekday hours,
	Worst hour of day,
	Avg hours per day with data,
	Count of epochs:
		All times
		Weekdays 6am-10am
		Weekdays 10am-4pm
		Weekdays 4pm-8pm
		Weekends 6am-8pm,
	1/0 NHS status

           
Author: Darren Conly
Last Updated: 9/2019
Updated by: <name>
Copyright:   (c) SACOG
SQL Flavor: SQL Server
*/

--==========PARAMETER VARIABLES=============================================================

--trying these per stack overflow answer
--https://stackoverflow.com/questions/62678904/resourceclosederror-attributeerror-when-using-pandas-read-sql-query-attributeerr
SET ANSI_WARNINGS OFF 
SET NOCOUNT ON

--"bad" travel time percentile
DECLARE @PctlCongested FLOAT SET @PctlCongested = 0.8

--free-flow speed time period
DECLARE @FFprdStart INT SET @FFprdStart = 20 --free-flow period starts at or after this time at night
DECLARE @FFprdEnd INT SET @FFprdEnd = 6 --free-flow period ends before this time in the morning

--list of weekdays
DECLARE @weekdays TABLE (day_name VARCHAR(9))
	INSERT INTO @weekdays VALUES ('Monday')
	INSERT INTO @weekdays VALUES ('Tuesday')
	INSERT INTO @weekdays VALUES ('Wednesday')
	INSERT INTO @weekdays VALUES ('Thursday')
	INSERT INTO @weekdays VALUES ('Friday')

--hour period break points, use 24-hour time
DECLARE @AMpeakStart INT SET @AMpeakStart = 6 --greater than or equal to this time
DECLARE @AMpeakEnd INT SET @AMpeakEnd = 10 --less than this time
DECLARE @MiddayStart INT SET @MiddayStart = 10 --greater than or equal to this time
DECLARE @MiddayEnd INT SET @MiddayEnd = 16 --less than this time
DECLARE @PMpeakStart INT SET @PMpeakStart = 16 --greater than or equal to this time
DECLARE @PMpeakEnd INT SET @PMpeakEnd = 20 --less than this time
DECLARE @WkdPrdStart INT SET @WkdPrdStart = 6 --greater than or equal to this time
DECLARE @WkdPrdEnd INT SET @WkdPrdEnd = 20 --less than this time

--===========TRAVEL TIME PERCENTILES==============================

--50th and 80th percentile TTs for AM peak
SELECT
	DISTINCT tmc_code,
	PERCENTILE_CONT(@PctlCongested)
		WITHIN GROUP (ORDER BY travel_time_seconds)
		OVER (PARTITION BY tmc_code) 
		AS tt_p80_ampk,
	PERCENTILE_CONT(0.5)
		WITHIN GROUP (ORDER BY travel_time_seconds)
		OVER (PARTITION BY tmc_code) 
		AS tt_p50_ampk
INTO #tt_pctl_ampk2
FROM npmrds_2023_alltmc_paxtruck_comb
WHERE DATENAME(dw, measurement_tstamp) IN (SELECT day_name FROM @weekdays) 
	AND DATEPART(hh, measurement_tstamp) >= @AMpeakStart 
	AND DATEPART(hh, measurement_tstamp) < @AMpeakEnd



SELECT TOP 100 * FROM #tt_pctl_ampk2

