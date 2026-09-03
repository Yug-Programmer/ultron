@echo off
title Ultron Autonomous Assistant
cd /d %~dp0
echo ===================================================
echo             STARTING ULTRON SYSTEM
echo ===================================================
.venv\Scripts\python.exe main.py
pause
