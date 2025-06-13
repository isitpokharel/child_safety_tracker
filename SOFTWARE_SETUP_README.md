# KiddoTrack-Lite: Development and Testing Environment Setup

## Software Requirements

### Development Environment

This application was developed using the following software and version numbers:

#### **Core Development Stack**
- **Python**: 3.10+ (Programming Language)
- **FastAPI**: 0.111.0 (Modern web framework for building APIs)
- **uvicorn**: 0.30.0 (Lightning-fast ASGI server implementation)
- **Rich**: 13.7.0 (Python library for rich text and terminal formatting)
- **Shapely**: 2.0.2 (Manipulation and analysis of geometric objects)
- **WebSockets**: 12.0 (WebSocket client and server implementation)

#### **Development Tools**
- **Git**: Version control system
- **pip**: Python package installer
- **Virtual Environment**: Python virtual environment manager

### Testing Environment

The application testing was performed using the following software:

#### **Testing Framework**
- **pytest**: 8.0.0 (Python testing framework)
- **coverage**: 7.4.0 (Code coverage measurement)
- **httpx**: 0.27.0 (HTTP client library for testing API endpoints)

#### **Testing Tools**
- **unittest**: Built-in Python testing framework (used alongside pytest)
- **Mock**: Built-in Python mocking library for unit tests

## System Requirements

### **Operating System**
- **Primary Development OS**: macOS 14.5.0 (Darwin 24.5.0)
- **Supported OS**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)

### **Hardware Requirements**
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 500MB free space
- **CPU**: Any modern 64-bit processor

## Setup Instructions

### 1. Prerequisites Installation

#### **Install Python 3.10+**
```bash
# macOS (using Homebrew)
brew install python@3.10

# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-pip

# Windows
# Download from https://www.python.org/downloads/
```

#### **Verify Python Installation**
```bash
python --version  # Should show Python 3.10.x or higher
pip --version      # Should show pip version
```

### 2. Application Setup

#### **Clone Repository**
```bash
git clone <your-repository-url>
cd CISC593
```

#### **Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### **Install Dependencies**
```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list
```

#### **Create Data Directory**
```bash
mkdir -p data
```

### 3. Development Environment Verification

#### **Test Basic Setup**
```bash
# Verify all modules can be imported
python -c "import fastapi, uvicorn, rich, pytest, coverage, httpx, shapely, websockets; print('All dependencies imported successfully')"
```

#### **Run Application Health Check**
```bash
# Start the API server (in one terminal)
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Test health endpoint (in another terminal)
curl http://localhost:8000/health
```

### 4. Testing Environment Setup

#### **Run Unit Tests**
```bash
# Run all tests
python run_all_tests.py

# Run specific test modules
pytest test_config.py -v
pytest test_geofence.py -v
pytest test_simulator.py -v
pytest test_logger.py -v
pytest test_api.py -v
```

#### **Generate Test Coverage Report**
```bash
# Run tests with coverage
coverage run -m pytest
coverage report -m
coverage html  # Generates HTML coverage report
```

#### **Test Individual Components**
```bash
# Test configuration module
python -m pytest test_config.py -v

# Test geofence module
python -m pytest test_geofence.py -v

# Test simulator module
python -m pytest test_simulator.py -v

# Test logger module
python -m pytest test_logger.py -v

# Test API module
python -m pytest test_api.py -v
```

## Development Workflow

### **Starting the Development Environment**
```bash
# 1. Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# 2. Start API server with auto-reload
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# 3. In separate terminals, run:
python parent_console.py    # Parent monitoring console
python child_simulator.py   # Child device simulator
```

### **Development Best Practices**
- Always work within the virtual environment
- Run tests before committing changes
- Use `uvicorn --reload` for development with auto-restart
- Check code coverage regularly
- Follow PEP 8 style guidelines

## Testing Strategy

### **Unit Testing**
- **Framework**: pytest 8.0.0
- **Coverage Target**: 80%+ code coverage
- **Test Types**: Unit tests, integration tests, API endpoint tests
- **Mocking**: Using unittest.mock for external dependencies

### **API Testing**
- **Client**: httpx 0.27.0 for HTTP request testing
- **WebSocket Testing**: Direct websockets library testing
- **Response Validation**: Pydantic model validation

### **Coverage Analysis**
- **Tool**: coverage 7.4.0
- **Reports**: HTML and terminal reports
- **Metrics**: Line coverage, branch coverage, function coverage

## Troubleshooting

### **Common Issues**

#### **Python Version Issues**
```bash
# Check Python version
python --version

# If version is < 3.10, install correct version
# Use pyenv or conda for version management
```

#### **Virtual Environment Issues**
```bash
# Recreate virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### **Dependency Conflicts**
```bash
# Clear pip cache and reinstall
pip cache purge
pip install --force-reinstall -r requirements.txt
```

#### **Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process or use different port
uvicorn api:app --port 8001
```

## Production Deployment

### **Production Requirements**
- Python 3.10+ with production WSGI server
- Reverse proxy (nginx recommended)
- Process manager (systemd, supervisor, or PM2)
- SSL/TLS certificates for HTTPS
- Database for persistent storage (if required)

### **Production Setup**
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **pytest Documentation**: https://docs.pytest.org/
- **Rich Documentation**: https://rich.readthedocs.io/
- **Shapely Documentation**: https://shapely.readthedocs.io/

---

**Note**: This README focuses specifically on the software environment and setup instructions. For detailed application documentation, architecture, and usage guide, refer to the main `README.md` file. 