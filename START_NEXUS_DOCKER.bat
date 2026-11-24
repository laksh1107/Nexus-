@echo off
cd /d "%~dp0"
if not exist .env (
  copy .env.example .env
  echo Created .env from .env.example. Edit it if you want to configure Gemini.
)
docker compose up --build
pause
