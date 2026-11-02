@echo off
cd /d "%~dp0"
fh_loader.exe --port=\\.\COM24 --memoryname=ufs --zlpawarehost=1 --search_path=. --sendxml=fill_b_lun2.xml,fill_b_lun4.xml,fill_b_lun0.xml --noprompt --showpercentagecomplete
