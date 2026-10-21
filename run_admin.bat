@echo off
title PyClean Pro (Modo Administrador)
chcp 65001 >nul
cd /d "%~dp0"

:: Verificar si ya tenemos privilegios de Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Ya estamos como Administrador
set "PYTHON_EXE="

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :found
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    goto :found
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto :found
)

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    goto :found
)

:found
"%PYTHON_EXE%" main.py
