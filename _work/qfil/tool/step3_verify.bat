@echo off
cd /d "%~dp0"
fh_loader.exe --port=\\.\COM24 --memoryname=ufs --zlpawarehost=1 --search_path=. --mainoutputdir=readback --sendxml=read_verify.xml --noprompt
