REM .venv exists
if exist .venv (
    rmdir /s /q .venv
)

REM make .venv
python -m venv .venv

REM install packages for .venv
call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements.txt
