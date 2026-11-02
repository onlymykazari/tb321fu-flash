@echo off
cd /d "%~dp0"
QSaharaServer.exe -p \\.\COM24 -s 13:prog_firehose_ddr.elf
fh_loader.exe --port=\\.\COM24 --memoryname=ufs --zlpawarehost=1 --search_path=. --mainoutputdir=readback --sendxml=read_b_check.xml --noprompt
