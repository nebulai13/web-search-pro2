#!/bin/bash
# Web Search Pro v2.0 - Installation Script
# Supports: macOS, Linux (Debian/Ubuntu, Fedora/RHEL, Arch)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║            WEB SEARCH PRO v2.0 - INSTALLER                        ║"
echo "║       Advanced Web & Darknet Search Tool                          ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        info "Detected: macOS"
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
        info "Detected: Debian/Ubuntu"
    elif [[ -f /etc/fedora-release ]]; then
        OS="fedora"
        info "Detected: Fedora"
    elif [[ -f /etc/arch-release ]]; then
        OS="arch"
        info "Detected: Arch Linux"
    elif [[ -f /etc/redhat-release ]]; then
        OS="rhel"
        info "Detected: RHEL/CentOS"
    else
        OS="unknown"
        warn "Unknown OS - will attempt generic installation"
    fi
}

# Check for Python 3.9+
check_python() {
    info "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 9 ]]; then
            success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python3"
        else
            warn "Python $PYTHON_VERSION found, but 3.9+ recommended"
            PYTHON_CMD="python3"
        fi
    else
        error "Python 3 not found. Please install Python 3.9 or higher."
    fi
}

# Install system dependencies
install_system_deps() {
    info "Installing system dependencies..."
    
    case $OS in
        macos)
            if ! command -v brew &> /dev/null; then
                warn "Homebrew not found. Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install tor 2>/dev/null || true
            success "System dependencies installed (macOS)"
            ;;
        debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3-pip python3-venv tor
            success "System dependencies installed (Debian/Ubuntu)"
            ;;
        fedora)
            sudo dnf install -y python3-pip tor
            success "System dependencies installed (Fedora)"
            ;;
        arch)
            sudo pacman -Sy --noconfirm python-pip tor
            success "System dependencies installed (Arch)"
            ;;
        rhel)
            sudo yum install -y python3-pip
            warn "Install Tor manually for RHEL/CentOS"
            ;;
        *)
            warn "Skipping system dependencies - install manually if needed"
            ;;
    esac
}

# Create virtual environment (optional)
setup_venv() {
    if [[ "$USE_VENV" == "yes" ]]; then
        info "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        source venv/bin/activate
        PYTHON_CMD="python"
        PIP_CMD="pip"
        success "Virtual environment created and activated"
    else
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
}

# Install Python dependencies
install_python_deps() {
    info "Installing Python dependencies..."
    
    # Upgrade pip first
    $PIP_CMD install --upgrade pip -q
    
    # Install requirements
    $PIP_CMD install -r requirements.txt -q
    
    success "Python dependencies installed"
}

# Create necessary directories
create_directories() {
    info "Creating directories..."
    
    mkdir -p logs results journal sessions config
    
    success "Directories created"
}

# Setup configuration
setup_config() {
    info "Setting up configuration..."
    
    # Create blacklist if it doesn't exist
    if [[ ! -f config/blacklist.txt ]]; then
        cat > config/blacklist.txt << 'EOF'
# URL Blacklist for Web Search Pro
# Add URLs or domains to block (one per line)
# Lines starting with # are comments

# Example malware domains (uncomment to enable)
# malware-domain.com
# suspicious-site.net

# Example tracking domains
# tracker.example.com
EOF
        success "Created config/blacklist.txt"
    fi
    
    # Check if YAML config exists
    if [[ -f config/websearchpro.yaml ]]; then
        success "Configuration file exists"
    else
        warn "config/websearchpro.yaml not found - using defaults"
    fi
}

# Start Tor service
setup_tor() {
    info "Setting up Tor..."
    
    case $OS in
        macos)
            if brew services list | grep -q "tor.*started"; then
                success "Tor is already running"
            else
                warn "Starting Tor service..."
                brew services start tor 2>/dev/null || true
                sleep 3
                if brew services list | grep -q "tor.*started"; then
                    success "Tor started successfully"
                else
                    warn "Could not start Tor. Start manually with: brew services start tor"
                fi
            fi
            ;;
        debian|fedora|rhel|arch)
            if systemctl is-active --quiet tor; then
                success "Tor is already running"
            else
                warn "Starting Tor service..."
                sudo systemctl start tor 2>/dev/null || true
                sudo systemctl enable tor 2>/dev/null || true
                if systemctl is-active --quiet tor; then
                    success "Tor started successfully"
                else
                    warn "Could not start Tor. Start manually with: sudo systemctl start tor"
                fi
            fi
            ;;
        *)
            warn "Please start Tor manually for darknet searches"
            ;;
    esac
}

# Verify installation
verify_installation() {
    info "Verifying installation..."
    
    # Test imports
    if $PYTHON_CMD -c "
from websearch import WebSearchPro
from src.state_manager import StateManager
from src.ranker import ResultRanker
print('All imports successful')
" 2>/dev/null; then
        success "All modules load correctly"
    else
        error "Module import failed. Check error messages above."
    fi
    
    # Test Tor connection
    if $PYTHON_CMD -c "
from search_engines import SearchEngineManager
m = SearchEngineManager()
if m.check_tor_connection():
    print('Tor: ONLINE')
else:
    print('Tor: OFFLINE')
" 2>/dev/null; then
        success "Search engine manager initialized"
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    INSTALLATION COMPLETE!                         ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo ""
    if [[ "$USE_VENV" == "yes" ]]; then
        echo "  # Activate virtual environment first:"
        echo "  source venv/bin/activate"
        echo ""
    fi
    echo "  # Interactive mode:"
    echo "  python3 websearch.py"
    echo ""
    echo "  # Single search:"
    echo "  python3 websearch.py \"your query\""
    echo ""
    echo "  # Deep search with reports:"
    echo "  python3 websearch.py --deep --report \"research topic\""
    echo ""
    echo "  # Include darknet (requires Tor):"
    echo "  python3 websearch.py -d \"privacy tools\""
    echo ""
    echo -e "${CYAN}New v2.0 Features:${NC}"
    echo "  --i2p          Include I2P network search"
    echo "  --resume ID    Resume a paused search"
    echo "  --report       Generate HTML/Markdown reports"
    echo ""
    echo -e "${CYAN}Interactive Commands:${NC}"
    echo "  /pause         Pause search and save checkpoint"
    echo "  /resume        Resume paused search"
    echo "  /sessions      List saved sessions"
    echo "  /report        Generate reports"
    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo "  README.md      Quick start guide"
    echo "  claude.md      Full API documentation"
    echo ""
    echo -e "${YELLOW}For help: python3 websearch.py --help${NC}"
    echo ""
}

# Main installation flow
main() {
    # Parse arguments
    USE_VENV="no"
    SKIP_TOR="no"
    SKIP_SYSTEM="no"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv)
                USE_VENV="yes"
                shift
                ;;
            --skip-tor)
                SKIP_TOR="yes"
                shift
                ;;
            --skip-system)
                SKIP_SYSTEM="yes"
                shift
                ;;
            --help|-h)
                echo "Usage: ./install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --venv         Create and use a virtual environment"
                echo "  --skip-tor     Skip Tor installation/setup"
                echo "  --skip-system  Skip system dependency installation"
                echo "  --help, -h     Show this help message"
                exit 0
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    # Run installation steps
    detect_os
    check_python
    
    if [[ "$SKIP_SYSTEM" != "yes" ]]; then
        install_system_deps
    fi
    
    setup_venv
    install_python_deps
    create_directories
    setup_config
    
    if [[ "$SKIP_TOR" != "yes" ]]; then
        setup_tor
    fi
    
    verify_installation
    print_usage
}

# Run main
main "$@"
