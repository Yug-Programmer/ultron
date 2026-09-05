@echo off
title Ultron AI System (.NET 10)
cd /d %~dp0
echo ===================================================
echo             STARTING ULTRON .NET SYSTEM
echo ===================================================
dotnet run --project Ultron.Net\Ultron.Net.csproj
pause
