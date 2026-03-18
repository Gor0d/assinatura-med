@echo off
title Assinatura MED - Parando servidor
echo.
echo  Parando servidor...
cd /d "%~dp0"
docker-compose down
echo.
echo  Servidor parado.
pause
