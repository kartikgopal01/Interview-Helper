@echo off
echo Setting up Interview Helper...

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install requirements
echo Installing requirements...
pip install -r requirements.txt

:: Initialize NLTK data
echo Downloading NLTK data...
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

echo.
echo Setup complete!
echo.
echo To start the application:
echo 1. Make sure MongoDB is running
echo 2. Run the following commands in separate terminals:
echo.
echo Terminal 1:
echo   call venv\Scripts\activate
echo   python app.py
echo.
echo Terminal 2:
echo   call venv\Scripts\activate
echo   python interview_server.py
echo.
echo Then access the application at http://localhost:5001
echo.
pause 