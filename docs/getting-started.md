# Getting started

## Portable download

Obtain `FileFlow-v1.2.2-windows-x64.zip` and `SHA256SUMS.txt` from the
[verified project release](https://github.com/Mohammed-Alharbi-1/FileFlow/releases/tag/v1.2.2).
No Python installation is needed.

Extract the full archive, keep `_internal` alongside `FileFlow.exe`, and start
the EXE. These unsigned binaries are not a Windows installer. Do not bypass
security protections automatically. Check the published hash with:

```powershell
Get-FileHash .\FileFlow-v1.2.2-windows-x64.zip -Algorithm SHA256
```

Choose a folder, confirm setup, then test a small set of your own sample files
before enabling automatic organization. Windows 11 x64 was tested; Windows 10
validation remains outstanding. Read the [user guide](user-guide.md).
