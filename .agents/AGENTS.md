When running release_manager.py or any build scripts in this project, NEVER use 'uv run'. ALWAYS use '.\.venv\Scripts\python.exe tools\release\release_manager.py'. This project uses requirements.txt and standard venv, so uv run creates a broken PyInstaller build.
When running main.py, ALWAYS use the flags '--noclean --no-timestamp' to avoid deleting user data.
