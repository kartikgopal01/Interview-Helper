@echo off
echo Starting Interview Server...

:: Activate virtual environment
call venv\Scripts\activate

:: Run the interview server
python interview_server.py 