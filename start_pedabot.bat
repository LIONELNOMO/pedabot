@echo off
title PedaBot - Lanceur
color 0A

echo ========================================================
echo        LANCEMENT DU SYSTEME PEDABOT (REACT + PYTHON)
echo ========================================================
echo.

REM %~dp0 = dossier ou se trouve CE fichier .bat
set "ROOT=%~dp0"

echo Dossier racine : %ROOT%
echo.

echo [1/2] Demarrage du Backend Python (port 8000)...
start "PedaBot - Backend Python" cmd /k "cd /d "%ROOT%backend" && python main.py"

REM Attendre 3 secondes que Python demarre
timeout /t 3 /nobreak > nul

echo [2/2] Demarrage du Frontend React (Vite)...
start "PedaBot - Frontend React" cmd /k "cd /d "%ROOT%pedabot-react" && npm run dev"

echo.
echo ========================================================
echo   Tout est lance !
echo   Frontend React  : http://localhost:5173/ (ou 5174)
echo   Backend Python  : http://localhost:8000/
echo   Docs API        : http://localhost:8000/docs
echo ========================================================
echo.
echo Appuyez sur une touche pour fermer CE lanceur.
pause > nul
