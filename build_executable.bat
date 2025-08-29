@echo off
REM site2pdf Executable Builder for Windows
REM This script builds a standalone executable for the site2pdf application

echo 🔨 Building site2pdf executable...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    exit /b 1
)

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

REM Clean previous builds
if exist "build" (
    echo 🧹 Cleaning previous build artifacts...
    rmdir /s /q "build"
)

if exist "dist" (
    echo 🧹 Cleaning previous distribution...
    rmdir /s /q "dist"
)

REM Build the executable using PyInstaller
echo 🚀 Building executable with PyInstaller...
pyinstaller site2pdf.spec
if errorlevel 1 (
    echo ❌ Build failed! Check the output above for errors.
    exit /b 1
)

REM Check if build was successful
if exist "dist\site2pdf.exe" (
    echo ✅ Build successful!
    echo 📍 Executable location: %cd%\dist\site2pdf.exe
    
    REM Test the executable
    echo 🧪 Testing executable...
    dist\site2pdf.exe --help >nul 2>&1
    if errorlevel 1 (
        echo ❌ Executable test failed!
        exit /b 1
    ) else (
        echo ✅ Executable test passed!
    )
    
    echo.
    echo 🎉 Build complete! You can now run the executable with:
    echo    dist\site2pdf.exe [options]
    echo.
    echo 📋 To distribute this executable:
    echo    1. Copy the 'dist\site2pdf.exe' file to the target system
    echo    2. Run it: site2pdf.exe [options]
    
) else (
    echo ❌ Build failed! Executable not found.
    exit /b 1
)