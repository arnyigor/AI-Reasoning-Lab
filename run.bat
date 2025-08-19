@echo off
rem Запускает основной Python-скрипт-лаунчер, передавая все аргументы.
chcp 65001 > nul

rem Ищем Python с помощью `py.exe` для надежности
py -3.10 run.py %*

echo.
pause
