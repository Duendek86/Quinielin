@echo off
set ZC_ROOT=C:\Users\Ramon\Documents\Zen-C
set ZC=C:\Users\Ramon\Documents\zc.exe
if not exist bin mkdir bin
%ZC% build src/main.zc -o bin/quinielin.exe
if %ERRORLEVEL% EQU 0 (
    echo Build successful: bin/quinielin.exe
) else (
    echo Build failed
)
