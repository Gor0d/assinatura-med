@echo off
title Assinatura MED - Servidor
echo.
echo  ==========================================
echo   Assinatura Medica Digital - Iniciando...
echo  ==========================================
echo.
cd /d "%~dp0"
docker-compose up --build -d
echo.
echo  Servidor iniciado!
echo  Acesse: http://10.224.7.157:5001
echo.
pause
