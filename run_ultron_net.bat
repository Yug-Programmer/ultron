@echo off
title Ultron AI System (.NET 10 & NLP Engine)
cd /d %~dp0
echo ===================================================
echo     STARTING ULTRON MULTIMODAL NLP SYSTEM
echo ===================================================

:: Start Local Python NLP Microservice in background
if exist .venv\Scripts\python.exe (
    echo [*] Engaging Local Python NLP Companion on http://127.0.0.1:8766...
    start /B .venv\Scripts\python.exe nlp_service.py > nul 2>&1
)

:: Run .NET 10 System
echo [*] Launching Ultron C# .NET 10 Engine & GUI...
dotnet run --project Ultron.Net\Ultron.Net.csproj

pause
