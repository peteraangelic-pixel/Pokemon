# bench_pc_v2.ps1 — Windows launcher: runs the Linux benchmark inside WSL2.
# libcg.so is a Linux ELF library, so the benchmark itself cannot run
# natively on Windows; this wrapper forwards to WSL2.
# Usage (PowerShell, from anywhere):  .\pokemon-agent\tools\bench_pc_v2.ps1
$ErrorActionPreference = 'Stop'
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    throw "WSL not found. Install WSL2:  wsl --install -d Ubuntu"
}
$agentDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wslPath = (wsl wslpath -a "$agentDir").Trim()
Write-Host "Running bench_pc_v2 in WSL2: $wslPath"
wsl bash -lc "cd '$wslPath' && bash tools/bench_pc_v2.sh"
