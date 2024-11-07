@echo off
REM 设置代码页为65001（UTF-8）
chcp 65001 >nul

REM 切换到脚本所在目录
cd /d %~dp0

REM 使用PyInstaller打包Python脚本
py -m PyInstaller --onefile --windowed --noconsole --icon=open.ico script.py

REM 打包完成后，暂停以查看输出
echo build success! Congratulations!
echo open exe file...
cd dist
start script.exe

pause 