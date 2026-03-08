@echo off
set SRC=D:\dev\plugin\toSketch\
set DST=%APPDATA%\FreeCAD\Mod\toSketch

echo Removing old install...
rmdir /s /q "%DST%" 2>nul

echo Copying plugin...
mkdir "%DST%" 2>nul
copy "%SRC%package.xml" "%DST%\" /y >nul
copy "%SRC%metadata.txt" "%DST%\" /y >nul
copy "%SRC%LICENSE" "%DST%\" /y >nul
xcopy "%SRC%freecad" "%DST%\freecad\" /e /i /q /y

echo Done.
