:: Batch script to delete all files within specified folder more than 1 day old
:: NOTE - this does not delete recursively. It only deletes files, not subfolders or subfolder contents
:: https://stackoverflow.com/questions/324267/batch-file-to-delete-files-older-than-a-specified-date
:: https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/forfiles

:: /P = path to specify, /D = number of days before (-) or after current date
:: /C = command string to execute, @file = the file you're iterating on
forfiles /P C:\Users\dconly\Desktop\Temporary\test_to_empty /D -1 /C "cmd /C Del @file"