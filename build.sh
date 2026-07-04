#!/bin/bash
# Script de build para Render - instala ODBC Driver 17 para SQL Server

set -e

echo "=== Instalando Microsoft ODBC Driver 17 ==="
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update -qq
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

echo "=== Instalando dependencias Python ==="
pip install -r requirements.txt

echo "=== Build completado ==="
