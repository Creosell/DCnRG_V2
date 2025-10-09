Command for generating .exe file 
pyinstaller main.py --onefile --name "ReportGenerator" --hidden-import "src.parse" --hidden-import "src.calculate" --hidden-import "src.report" --hidden-import "src.helpers"
