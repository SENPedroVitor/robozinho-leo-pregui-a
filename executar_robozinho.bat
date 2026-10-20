@echo off
chcp 65001 > nul
title 🤖 Robozinho do Leo - Organizador de Arquivos e PDFs

echo ============================================================
echo        ROBOZINHO DO LEO - ORGANIZADOR & MESCLADOR
echo ============================================================
echo.

:: 1. Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ATENCAO] O Python nao foi encontrado no seu computador!
    echo.
    echo Para usar o robozinho, voce so precisa instalar o Python:
    echo 1. Baixe em: https://www.python.org/downloads/
    echo 2. Na instalacao, marque a caixinha: "Add python.exe to PATH"
    echo.
    echo Depois de instalar, e so dar 2 cliques neste arquivo de novo!
    echo ============================================================
    pause
    exit /b 1
)

:: 2. Instala biblioteca necessaria se ainda nao tiver (de forma silenciosa)
python -c "import pypdf" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Configurando ambiente pela primeira vez, aguarde alguns segundos...
    python -m pip install --quiet pypdf
    echo [OK] Ambiente configurado com sucesso!
    echo.
)

:: 3. Executa o Robozinho
python organizador_arquivos.py

echo.
pause
