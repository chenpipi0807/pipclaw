@echo off
wt new-tab --title "PipClaw" -d "D:\PIP-Cli\pipclaw" powershell -NoExit -Command "pipclaw" ^; split-pane -V --size 0.45 --title "Yazi" powershell -NoExit -File "D:\PIP-Cli\pipclaw\launch-yazi.ps1"
