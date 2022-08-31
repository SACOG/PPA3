/*

INSTRUCTIONS:
1 - In ArcPro, right-click the database > New > Database View
2 - set view name
3 - Copy/pasted everything below starting at "SELECT" into the "definition" prompt
	***Make sure field names are correct AND that you do in Pro interface, not in SQL Server


*/

--CREATE VIEW [owner].[project_joined_data_test] AS  
SELECT    
	m.project_join_id, 
	[ProjName], 
	Jurisdiction, 
	[ProjType], 
	[PerfOutcomes], 
	[ADT], 
	[SpeedLmt], 
	[PCI], 
	[TimeCreated],
	[Shape],
	[report_val1], 
	[report_val2]  
from owner.PROJECT_MASTER_TEST m   
	LEFT JOIN owner.PROJECT_DATA_TEST d    
		ON m.project_join_id = d.project_join_id


