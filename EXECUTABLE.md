# 🚀 Creating Standalone Executables

This guide explains how to create standalone executables for the site2pdf application using PyInstaller.

## 📋 Overview

The standalone executable allows users to run site2pdf without having Python installed on their system. All dependencies are bundled into a single file for easy distribution.

## 🛠️ Building the Executable

### Quick Build (Recommended)

Use the provided build scripts for automated building:

**Linux/macOS:**
```bash
./build_executable.sh
```

**Windows:**
```bash
build_executable.bat
```

### Manual Build

If you prefer manual control:

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Build using the spec file
pyinstaller site2pdf.spec

# Or build with basic options
pyinstaller --onefile --name site2pdf src/main.py
```

## 📁 Files Created for Executable Support

- **`setup.py`**: Python packaging configuration
- **`site2pdf.spec`**: PyInstaller configuration with optimizations
- **`build_executable.sh`**: Linux/macOS build script
- **`build_executable.bat`**: Windows build script
- **`requirements.txt`**: Updated with pyinstaller dependency

## ⚙️ PyInstaller Configuration

The `site2pdf.spec` file includes optimizations for:

- **Hidden Imports**: Ensures all required modules are included
- **Data Files**: Bundles configuration files and weasyprint assets
- **Size Optimization**: UPX compression enabled
- **Cross-Platform**: Works on Linux, macOS, and Windows

## 📦 Executable Details

**Output:**
- **Location**: `dist/site2pdf` (Linux/macOS) or `dist/site2pdf.exe` (Windows)
- **Size**: ~47MB (includes all Python dependencies)
- **Dependencies**: Self-contained, no external requirements

**Features:**
- ✅ All CLI functionality preserved
- ✅ Configuration file support (config.yaml)
- ✅ Full weasyprint PDF generation
- ✅ Cache system support
- ✅ Todo management system
- ✅ Preview mode and interactive features
- ✅ Complete authentication system support
- ✅ Session persistence and credential management

## 🚀 Distribution

### For End Users

1. **Download the executable** from releases or build locally
2. **Make executable** (Linux/macOS): `chmod +x site2pdf`
3. **Run directly**: `./site2pdf [options] <url>`

### Usage Examples

```bash
# Basic website scraping
./dist/site2pdf https://docs.python.org

# Advanced options
./dist/site2pdf https://example.com --format markdown --max-depth 3 --verbose

# Preview mode
./dist/site2pdf https://example.com --preview

# Resume from cache
./dist/site2pdf https://example.com --resume session_id

# Authentication examples
./dist/site2pdf https://protected-site.com --username myuser --password mypass
./dist/site2pdf https://protected-site.com --auth  # Uses environment variables
./dist/site2pdf https://intranet.company.com --username employee

# Check version
./dist/site2pdf --version
```

## 🔧 Troubleshooting

### Common Build Issues

**1. Missing Dependencies**
```bash
# Solution: Install all requirements first
pip install -r requirements.txt
```

**2. WeasyPrint Dependencies**
```bash
# Linux: Install system dependencies
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# macOS: Install via Homebrew
brew install cairo pango gdk-pixbuf libffi
```

**3. Large Executable Size**
- This is normal due to bundled dependencies
- WeasyPrint and its dependencies contribute significantly to size
- Consider using `--exclude-module` in spec file for unused modules

### Runtime Issues

**1. Configuration Files**
- Ensure `config.yaml` is in the same directory as executable
- Or specify path with `--config` option

**2. Permissions**
- Make sure executable has run permissions
- Ensure output directory is writable

**3. Authentication Issues**
- Set environment variables for credentials:
  ```bash
  export SITE2PDF_AUTH_USERNAME="your-username"
  export SITE2PDF_AUTH_PASSWORD="your-password"
  ```
- For site-specific credentials:
  ```bash
  export SITE2PDF_EXAMPLE_COM_USERNAME="site-user"
  export SITE2PDF_EXAMPLE_COM_PASSWORD="site-pass"
  ```

## 🌍 Cross-Platform Building

### Building for Multiple Platforms

PyInstaller creates executables for the platform it runs on. For multi-platform distribution:

**Linux Executable:**
```bash
# Build on Linux system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./build_executable.sh
```

**macOS Executable:**
```bash
# Build on macOS system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./build_executable.sh
```

**Windows Executable:**
```cmd
# Build on Windows system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
build_executable.bat
```

## 📊 Performance Considerations

**Startup Time:**
- Executable has ~2-3 second startup overhead
- This is normal for PyInstaller executables
- Actual scraping performance is identical to Python version

**Memory Usage:**
- Slightly higher memory usage due to bundled runtime
- Difference is negligible during actual operation

**File I/O:**
- Temporary extraction of some resources on first run
- Subsequent runs are faster

## 🔄 Updating Executables

When updating the application:

1. **Update source code**
2. **Test with Python version**
3. **Rebuild executable**: `./build_executable.sh`
4. **Test executable version**
5. **Distribute updated executable**

## 📋 Deployment Checklist

- [ ] All dependencies in requirements.txt
- [ ] PyInstaller spec file updated
- [ ] Build script tested on target platform
- [ ] Executable tested with various options
- [ ] Configuration files included
- [ ] Documentation updated
- [ ] File permissions set correctly

## 🆘 Support

For executable-specific issues:

1. **Check build output** for warnings or errors
2. **Test with `--verbose`** flag for detailed logging  
3. **Compare behavior** with Python version
4. **Check system dependencies** (especially for WeasyPrint)
5. **Verify file permissions** and paths

For more help, see the main README.md troubleshooting section.