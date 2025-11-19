#!/bin/bash

###############################################################################
# NASDAQ Stock Agent - Linode Deployment Script
# 
# This script automates the deployment of the NASDAQ Stock Agent on Linode
# instances. It handles both fresh installations and updates.
#
# Usage:
#   sudo ./deploy_linode.sh           # Fresh installation
#   sudo ./deploy_linode.sh --update  # Update existing installation
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="nasdaq-agent"
APP_DIR="/opt/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
APP_USER="${APP_NAME}"
APP_GROUP="${APP_NAME}"
PYTHON_VERSION="3.11"
SERVICE_NAME="${APP_NAME}.service"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Parse command line arguments
UPDATE_MODE=false
if [ "$1" == "--update" ]; then
    UPDATE_MODE=true
    log_info "Running in UPDATE mode"
else
    log_info "Running in INSTALL mode"
fi

###############################################################################
# Task 1.1: Install System Dependencies
###############################################################################

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect operating system"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VERSION"
    
    if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
        install_dependencies_ubuntu
    else
        log_error "Unsupported operating system: $OS"
        log_error "Supported: Ubuntu 22.04+, Debian 11+"
        exit 1
    fi
    
    # Verify Python installation
    verify_python_installation
}

install_dependencies_ubuntu() {
    log_info "Installing dependencies for Ubuntu/Debian..."
    
    # Update package list
    log_info "Updating package list..."
    apt-get update -y
    
    # Install required packages
    log_info "Installing required packages..."
    apt-get install -y \
        software-properties-common \
        build-essential \
        git \
        curl \
        wget \
        python3-pip \
        python3-venv \
        python3-dev \
        libssl-dev \
        libffi-dev \
        ufw
    
    # Check Python version
    PYTHON_CURRENT=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "Current Python version: $PYTHON_CURRENT"
    
    # Install Python 3.11+ if needed
    if ! command -v python${PYTHON_VERSION} &> /dev/null; then
        log_info "Python ${PYTHON_VERSION} not found, installing from deadsnakes PPA..."
        add-apt-repository ppa:deadsnakes/ppa -y
        apt-get update -y
        apt-get install -y \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-venv \
            python${PYTHON_VERSION}-dev
    else
        log_info "Python ${PYTHON_VERSION} is already installed"
    fi
}

verify_python_installation() {
    log_info "Verifying Python installation..."
    
    # Try python3.11 first, fall back to python3
    if command -v python${PYTHON_VERSION} &> /dev/null; then
        PYTHON_CMD="python${PYTHON_VERSION}"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        log_warn "Using system Python ${PYTHON_VERSION}"
    else
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Verify Python version is 3.9+
    PYTHON_MAJOR=$(${PYTHON_CMD} --version | cut -d' ' -f2 | cut -d'.' -f1)
    PYTHON_MINOR=$(${PYTHON_CMD} --version | cut -d' ' -f2 | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        log_error "Python 3.9+ is required, found ${PYTHON_MAJOR}.${PYTHON_MINOR}"
        exit 1
    fi
    
    log_info "Python verification successful: ${PYTHON_CMD} ($(${PYTHON_CMD} --version))"
    
    # Verify pip
    if ! ${PYTHON_CMD} -m pip --version &> /dev/null; then
        log_error "pip is not installed for ${PYTHON_CMD}"
        exit 1
    fi
    
    log_info "pip verification successful: $(${PYTHON_CMD} -m pip --version)"
}

###############################################################################
# Task 1.2: Create Directory Structure
###############################################################################

create_directory_structure() {
    log_info "Creating directory structure..."
    
    # Create application directory
    if [ ! -d "$APP_DIR" ]; then
        log_info "Creating application directory: $APP_DIR"
        mkdir -p "$APP_DIR"
    else
        log_info "Application directory already exists: $APP_DIR"
    fi
    
    # Create log directory
    if [ ! -d "$LOG_DIR" ]; then
        log_info "Creating log directory: $LOG_DIR"
        mkdir -p "$LOG_DIR"
    else
        log_info "Log directory already exists: $LOG_DIR"
    fi
    
    # Create subdirectories for logs
    mkdir -p "$LOG_DIR/archive"
    
    log_info "Directory structure created successfully"
}

###############################################################################
# Task 1.3: Create System User
###############################################################################

create_system_user() {
    log_info "Creating system user..."
    
    # Check if user already exists
    if id "$APP_USER" &>/dev/null; then
        log_info "User $APP_USER already exists"
    else
        log_info "Creating system user: $APP_USER"
        
        # Create system user with no shell and no home directory
        useradd --system \
                --no-create-home \
                --shell /usr/sbin/nologin \
                --comment "NASDAQ Stock Agent Service User" \
                "$APP_USER"
        
        log_info "System user $APP_USER created successfully"
    fi
    
    # Set ownership and permissions for application directory
    log_info "Setting ownership for $APP_DIR"
    chown -R ${APP_USER}:${APP_GROUP} "$APP_DIR"
    chmod 755 "$APP_DIR"
    
    # Set ownership and permissions for log directory
    log_info "Setting ownership for $LOG_DIR"
    chown -R ${APP_USER}:${APP_GROUP} "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    chmod 755 "$LOG_DIR/archive"
    
    log_info "Permissions configured successfully"
}

###############################################################################
# Task 1.4: Setup Python Virtual Environment
###############################################################################

setup_virtual_environment() {
    log_info "Setting up Python virtual environment..."
    
    VENV_DIR="$APP_DIR/venv"
    
    # Copy application files to APP_DIR if not in update mode
    if [ "$UPDATE_MODE" = false ]; then
        log_info "Copying application files to $APP_DIR"
        
        # Get the directory where this script is located
        SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
        
        # Copy all files except venv, logs, and cache
        rsync -av --exclude='venv' \
                  --exclude='logs' \
                  --exclude='__pycache__' \
                  --exclude='*.pyc' \
                  --exclude='.git' \
                  --exclude='.env' \
                  "$SCRIPT_DIR/" "$APP_DIR/" || {
            # If rsync not available, use cp
            log_warn "rsync not found, using cp instead"
            cp -r "$SCRIPT_DIR"/* "$APP_DIR/" 2>/dev/null || true
            cp -r "$SCRIPT_DIR"/.[!.]* "$APP_DIR/" 2>/dev/null || true
        }
        
        # Set ownership
        chown -R ${APP_USER}:${APP_GROUP} "$APP_DIR"
    fi
    
    # Create or update virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment at $VENV_DIR"
        sudo -u $APP_USER ${PYTHON_CMD} -m venv "$VENV_DIR"
    else
        log_info "Virtual environment already exists at $VENV_DIR"
    fi
    
    # Upgrade pip
    log_info "Upgrading pip..."
    sudo -u $APP_USER "$VENV_DIR/bin/pip" install --upgrade pip
    
    # Install/update dependencies
    if [ -f "$APP_DIR/requirements.txt" ]; then
        log_info "Installing Python dependencies from requirements.txt..."
        sudo -u $APP_USER "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
        
        # Verify installation
        log_info "Verifying package installation..."
        INSTALLED_PACKAGES=$(sudo -u $APP_USER "$VENV_DIR/bin/pip" list | wc -l)
        log_info "Installed $INSTALLED_PACKAGES packages"
        
        # Check for critical packages
        CRITICAL_PACKAGES=("fastapi" "uvicorn" "anthropic" "langchain")
        for package in "${CRITICAL_PACKAGES[@]}"; do
            if sudo -u $APP_USER "$VENV_DIR/bin/pip" show "$package" &>/dev/null; then
                log_info "✓ $package installed"
            else
                log_error "✗ $package NOT installed"
                exit 1
            fi
        done
        
        log_info "All critical packages verified successfully"
    else
        log_error "requirements.txt not found at $APP_DIR/requirements.txt"
        exit 1
    fi
    
    log_info "Virtual environment setup complete"
}

###############################################################################
# Task 1.5: Configure Firewall (UFW for Linode)
###############################################################################

configure_firewall() {
    log_info "Configuring UFW firewall for Linode..."
    
    # Install ufw if not present
    if ! command -v ufw &> /dev/null; then
        log_info "Installing ufw..."
        apt-get install -y ufw
    fi
    
    # Configure default policies
    log_info "Setting default policies..."
    ufw --force default deny incoming
    ufw --force default allow outgoing
    
    # Allow SSH (important - do this first!)
    log_info "Allowing SSH (port 22)..."
    ufw --force allow 22/tcp comment 'SSH'
    
    # Allow REST API
    log_info "Allowing REST API (port 8000)..."
    ufw --force allow 8000/tcp comment 'NASDAQ Agent REST API'
    
    # Allow NEST A2A
    log_info "Allowing NEST A2A (port 6000)..."
    ufw --force allow 6000/tcp comment 'NASDAQ Agent NEST A2A'
    
    # Enable firewall
    log_info "Enabling UFW..."
    ufw --force enable
    
    # Show status
    log_info "Firewall status:"
    ufw status numbered
    
    log_info "UFW configuration complete"
}

###############################################################################
# Task 2: Setup Systemd Service
###############################################################################

setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Copy service file
    if [ -f "$SCRIPT_DIR/${SERVICE_NAME}" ]; then
        log_info "Copying service file to $SERVICE_FILE"
        cp "$SCRIPT_DIR/${SERVICE_NAME}" "$SERVICE_FILE"
        chmod 644 "$SERVICE_FILE"
    else
        log_error "Service file not found: $SCRIPT_DIR/${SERVICE_NAME}"
        exit 1
    fi
    
    # Reload systemd daemon
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload
    
    # Enable service to start on boot
    log_info "Enabling ${SERVICE_NAME} to start on boot..."
    systemctl enable ${SERVICE_NAME}
    
    log_info "Systemd service setup complete"
    log_info "Service can be controlled with:"
    log_info "  - Start:   sudo systemctl start ${SERVICE_NAME}"
    log_info "  - Stop:    sudo systemctl stop ${SERVICE_NAME}"
    log_info "  - Restart: sudo systemctl restart ${SERVICE_NAME}"
    log_info "  - Status:  sudo systemctl status ${SERVICE_NAME}"
    log_info "  - Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
}

###############################################################################
# Task 4: Setup Log Rotation
###############################################################################

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    LOGROTATE_FILE="/etc/logrotate.d/${APP_NAME}"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Copy logrotate configuration
    if [ -f "$SCRIPT_DIR/logrotate-${APP_NAME}" ]; then
        log_info "Copying logrotate configuration to $LOGROTATE_FILE"
        cp "$SCRIPT_DIR/logrotate-${APP_NAME}" "$LOGROTATE_FILE"
        chmod 644 "$LOGROTATE_FILE"
    else
        log_error "Logrotate configuration not found: $SCRIPT_DIR/logrotate-${APP_NAME}"
        exit 1
    fi
    
    # Verify logrotate configuration
    log_info "Verifying logrotate configuration..."
    if logrotate -d "$LOGROTATE_FILE" &>/dev/null; then
        log_info "Logrotate configuration is valid"
    else
        log_warn "Logrotate configuration validation failed (non-critical)"
    fi
    
    log_info "Log rotation setup complete"
    log_info "Logs will be rotated daily and kept for 30 days"
}

###############################################################################
# Deployment Verification
###############################################################################

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if .env file exists
    if [ ! -f "$APP_DIR/.env" ]; then
        log_warn ".env file not found at $APP_DIR/.env"
        log_warn "Please create and configure .env file before starting the service"
        return
    fi
    
    # Validate environment configuration
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    if [ -f "$SCRIPT_DIR/validate_env.sh" ]; then
        log_info "Running environment validation..."
        if "$SCRIPT_DIR/validate_env.sh" "$APP_DIR/.env"; then
            log_info "Environment validation passed"
        else
            log_warn "Environment validation failed"
            log_warn "Please fix configuration issues before starting the service"
            return
        fi
    fi
    
    # Start the service if in update mode
    if [ "$UPDATE_MODE" = true ]; then
        log_info "Restarting service..."
        systemctl restart ${SERVICE_NAME}
        
        # Wait for service to start
        log_info "Waiting for service to start (up to 30 seconds)..."
        for i in {1..30}; do
            if systemctl is-active --quiet ${SERVICE_NAME}; then
                log_info "Service started successfully"
                break
            fi
            sleep 1
        done
        
        # Check service status
        if systemctl is-active --quiet ${SERVICE_NAME}; then
            log_info "Service is running"
            
            # Run health check
            sleep 5  # Give service time to fully initialize
            if [ -f "$APP_DIR/health_check.sh" ]; then
                log_info "Running health check..."
                if "$APP_DIR/health_check.sh"; then
                    log_info "✓ Deployment verification successful!"
                else
                    log_error "✗ Health check failed"
                    log_error "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
                fi
            fi
        else
            log_error "Service failed to start"
            log_error "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
        fi
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    log_info "========================================="
    log_info "NASDAQ Stock Agent - Linode Deployment"
    log_info "========================================="
    
    # Task 1.1: Install system dependencies
    install_system_dependencies
    
    # Task 1.2: Create directory structure
    if [ "$UPDATE_MODE" = false ]; then
        create_directory_structure
        
        # Task 1.3: Create system user
        create_system_user
    else
        log_info "Skipping directory and user creation (update mode)"
    fi
    
    # Task 1.4: Setup Python virtual environment (or update in update mode)
    if [ "$UPDATE_MODE" = true ]; then
        log_info "Updating application code..."
        cd "$APP_DIR"
        
        # Check if it's a git repository
        if [ -d ".git" ]; then
            log_info "Pulling latest code from git..."
            sudo -u $APP_USER git pull
        else
            log_warn "Not a git repository, skipping code update"
            log_warn "To update, manually copy new files to $APP_DIR"
        fi
    fi
    
    setup_virtual_environment
    
    # Task 1.5: Configure firewall
    if [ "$UPDATE_MODE" = false ]; then
        configure_firewall
    else
        log_info "Skipping firewall configuration (update mode)"
    fi
    
    # Task 2: Setup systemd service
    setup_systemd_service
    
    # Task 4: Setup log rotation
    if [ "$UPDATE_MODE" = false ]; then
        setup_log_rotation
    else
        log_info "Skipping log rotation setup (update mode)"
    fi
    
    # Verify deployment
    verify_deployment
    
    log_info "========================================="
    log_info "Deployment script execution complete!"
    log_info "========================================="
    echo ""
    
    if [ "$UPDATE_MODE" = false ]; then
        log_info "Next steps:"
        log_info "1. Configure environment variables:"
        log_info "   sudo nano $APP_DIR/.env"
        log_info "   (Update ANTHROPIC_API_KEY and other settings)"
        log_info ""
        log_info "2. Set secure permissions on .env file:"
        log_info "   sudo chmod 600 $APP_DIR/.env"
        log_info "   sudo chown ${APP_USER}:${APP_GROUP} $APP_DIR/.env"
        log_info ""
        log_info "3. Validate environment configuration:"
        log_info "   sudo $APP_DIR/validate_env.sh $APP_DIR/.env"
        log_info ""
        log_info "4. Start the service:"
        log_info "   sudo systemctl start ${SERVICE_NAME}"
        log_info ""
        log_info "5. Check service status:"
        log_info "   sudo systemctl status ${SERVICE_NAME}"
        log_info ""
        log_info "6. View logs:"
        log_info "   sudo journalctl -u ${SERVICE_NAME} -f"
        log_info ""
        log_info "7. Run health check:"
        log_info "   $APP_DIR/health_check.sh"
        log_info ""
        log_info "Linode-specific notes:"
        log_info "- Firewall configured with UFW"
        log_info "- Ports 22, 8000, 6000 are open"
        log_info "- Update your Linode firewall rules if needed"
    else
        log_info "Update complete!"
        log_info "Service status:"
        systemctl status ${SERVICE_NAME} --no-pager || true
    fi
}

# Run main function
main
