@echo off
if not exist bin mkdir bin
zc build src/main.zc -o bin/quinielin.exe
if %ERRORLEVEL% EQU 0 (
    echo Build successful: bin/quinielin.exe
) else (
    echo Build failed
)
