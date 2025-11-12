Create local environment
````bash
  python -m venv .venv
````
Activation of venv:\
Windows
````bash
   .venv\Scripts\activate
````
macOS and Linux
````bash
  source .venv/bin/activate
````
Install dependencies
````bash
  pip install -r requirements.txt
````
Command for generating .exe file
```bash
  pyinstaller main.py --onefile --name "ReportGenerator" --hidden-import "src.parse" --hidden-import "src.calculate" --hidden-import "src.report" --hidden-import "src.helpers" --distpath .
```

TODO:
1) Optimize names for variables in JSON reports, make one name across all functions
2) Optimize temp working folders
3) Add support for configuration enabled/disabled tests through YAML file (can be mixed with optimizing names)
4) Optimize using of color_space.yaml
5) Uploading reports result to cloud
6) Change report to HTML

