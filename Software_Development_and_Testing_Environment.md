# Software Development and Testing Environment Documentation

**KiddoTrack-Lite Child Safety Monitoring System**  
**Date:** December 16, 2024  
**Version:** 1.0.0

---

## Development Software and Versions

### Core Development Environment

**Operating System:**
- macOS 15.5 (Darwin 24.5.0) on ARM64 architecture
- Compatible with: Linux (Ubuntu 20.04+), Windows 10/11, macOS 11+

**Python Environment:**
- **Python:** 3.10.8 (Primary development version)
- **Package Manager:** pip 22.3.1
- **Virtual Environment:** Native Python venv
- **Shell:** zsh (macOS default)

### Development Dependencies

**Core Framework:**
```
fastapi==0.111.0           # REST API framework
uvicorn==0.30.0           # ASGI server
pydantic==2.11.5          # Data validation
starlette==0.37.2         # Web framework base
```

**User Interface:**
```
rich==13.7.0              # Terminal UI framework
```

**HTTP Client:**
```
httpx==0.27.0             # Async HTTP client
```

**Geospatial:**
```
shapely==2.0.2            # Geometric calculations
```

**WebSocket:**
```
websockets==12.0          # WebSocket support
```

**Development Tools:**
```
python-dotenv==1.1.0      # Environment variable management
jinja2>=2.11.2            # Template engine
typing-extensions>=4.8.0  # Type annotations
```

## Testing Software and Versions

### Testing Framework
```
pytest==8.0.0            # Primary testing framework
pytest-json-report==1.5.0 # JSON test reporting
pytest-metadata==3.1.1   # Test metadata collection
pytest-anyio==4.4.0      # Async testing support
```

### Code Coverage
```
coverage==7.4.0          # Code coverage analysis
```

### Testing Dependencies
```
pluggy==1.6.0            # Plugin management
iniconfig==2.1.0         # Configuration parsing
packaging>=20             # Package version handling
tomli>=1.0.0             # TOML configuration
exceptiongroup>=1        # Exception handling
```

### Mock and Fixtures
- **unittest.mock** (Python standard library)
- **pytest fixtures** for test setup
- **Custom mocks** for external dependencies

---

## Development Environment Setup

### Prerequisites
1. **Python 3.10+** installed on your system
2. **Git** for version control
3. **Terminal/Command Prompt** with shell access

### Initial Setup

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd CISC593
```

#### 2. Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, rich, httpx; print('Dependencies installed successfully')"
```

#### 4. Create Data Directory
```bash
mkdir -p data
```

#### 5. Environment Configuration (Optional)
```bash
# Create .env file for custom configuration
cat > .env << EOF
# Logger Configuration
LOGGER_BUFFER_SIZE=50
LOG_DIRECTORY=data

# Simulator Configuration  
HOME_LATITUDE=40.7128
HOME_LONGITUDE=-74.0060
UPDATE_FREQUENCY=1.0

# API Configuration
API_HOST=localhost
API_PORT=8000

# Geofence Configuration
DEFAULT_GEOFENCE_RADIUS=1000.0
EOF
```

### Development Workflow

#### Running the Application
```bash
# Start the API server
python3 -m uvicorn api:app --host localhost --port 8000 --reload

# Run the parent console (separate terminal)
python3 parent_console.py

# Run the child simulator (separate terminal)  
python3 child_simulator.py
```

#### Code Validation
```bash
# Check syntax
python3 -m py_compile *.py

# Import verification
python3 -c "import api, simulator, geofence, logger, config"
```

---

## Testing Environment Setup

### Test Dependencies Installation
```bash
# Install testing dependencies (if not already installed)
pip install pytest==8.0.0 pytest-json-report==1.5.0 coverage==7.4.0
```

### Test Directory Structure
```
CISC593/
├── test_geofence.py          # Geofence module tests
├── test_simulator.py         # Simulator module tests  
├── test_logger.py            # Logger module tests
├── test_api.py               # API module tests
├── test_config.py            # Configuration module tests
├── test_parent_console.py    # Parent console tests
├── test_child_simulator.py   # Child simulator tests
├── run_all_tests.py          # Test runner script
└── reports/                  # Test reports directory
```

### Running Tests

#### Individual Module Tests
```bash
# Test specific module
pytest test_geofence.py -v

# Test with coverage
pytest test_geofence.py --cov=geofence --cov-report=html

# Test with JSON report
pytest test_geofence.py --json-report --json-report-file=reports/geofence_report.json
```

#### Complete Test Suite
```bash
# Run all tests
python3 run_all_tests.py

# Alternative: Run with pytest
pytest -v --tb=short

# Run with coverage for all modules
pytest --cov=. --cov-report=html --cov-report=term
```

#### Test Configuration
```bash
# Create pytest configuration (optional)
cat > pytest.ini << EOF
[tool:pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
EOF
```

### Test Report Generation
```bash
# Generate comprehensive test reports
python3 run_all_tests.py

# Reports will be saved to:
# - reports/test_summary.json    # JSON summary
# - reports/test_summary.md      # Markdown summary  
# - reports/*_report.json        # Individual module reports
```

---

## Continuous Integration Setup

### GitHub Actions (Example)
```yaml
name: KiddoTrack-Lite Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest coverage
    
    - name: Run tests
      run: python3 run_all_tests.py
    
    - name: Upload test reports
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: reports/
```

---

## Development IDE Configuration

### VS Code Setup
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["."],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black"
}
```

### PyCharm Setup
1. Set Python interpreter to `venv/bin/python`
2. Configure test runner to use pytest
3. Set project root to CISC593 directory
4. Configure code style to use Black formatter

---

## Troubleshooting

### Common Issues

#### Missing Dependencies
```bash
# Error: ModuleNotFoundError
# Solution: Reinstall dependencies
pip install -r requirements.txt
```

#### Import Errors
```bash
# Error: Cannot import modules
# Solution: Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Test Failures
```bash
# Error: Tests failing due to missing directories
# Solution: Create required directories
mkdir -p data reports
```

#### Permission Issues (macOS/Linux)
```bash
# Error: Permission denied
# Solution: Fix permissions
chmod +x *.py
```

### Performance Optimization

#### For Development
- Use `--reload` flag with uvicorn for auto-reloading
- Set `PYTHONPATH` to avoid import issues
- Use virtual environment to isolate dependencies

#### For Testing
- Run tests in parallel: `pytest -n auto` (requires pytest-xdist)
- Use test markers: `pytest -m "not slow"`
- Skip integration tests: `pytest -k "not integration"`

---

## System Requirements

### Minimum Requirements
- **CPU:** 1 GHz processor
- **RAM:** 2 GB available memory
- **Storage:** 500 MB free space
- **Network:** Internet connection for dependencies

### Recommended Requirements
- **CPU:** 2+ GHz multi-core processor
- **RAM:** 4+ GB available memory
- **Storage:** 2+ GB free space
- **Network:** Broadband internet connection

### Platform Compatibility
- ✅ **macOS:** 11+ (Intel and Apple Silicon)
- ✅ **Linux:** Ubuntu 20.04+, CentOS 8+, Debian 10+
- ✅ **Windows:** 10/11 with Python 3.10+

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-16 | Initial release with complete test suite |

---

**Document Prepared By:** KiddoTrack-Lite Development Team  
**Last Updated:** December 16, 2024  
**Next Review:** January 16, 2025 