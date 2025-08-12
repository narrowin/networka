#!/bin/bash
# Installation script for nw completions (bash, zsh, fish)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPLETION_BASH="${SCRIPT_DIR}/bash_completion_nw.sh"
COMPLETION_ZSH="${SCRIPT_DIR}/zsh_completion_nw.zsh"
COMPLETION_FISH="${SCRIPT_DIR}/fish_completion_nw.fish"

print_status "Installing nw shell completions..."

# Check if we have bash-completion installed
if ! command -v bash >/dev/null 2>&1; then
    print_error "bash is not available"
    exit 1
fi

# Flags controlling which shells to install for (default: all)
DO_BASH=1
DO_ZSH=1
DO_FISH=1

# Method 1: Try system-wide installation (requires sudo)
install_system_wide() {
    print_status "Attempting system-wide installation..."

    local os
    os="$(uname -s)"

    # Bash
    local bash_dir=""
    if [[ -d "/usr/share/bash-completion/completions" ]]; then
        bash_dir="/usr/share/bash-completion/completions"
    elif [[ -d "/etc/bash_completion.d" ]]; then
        bash_dir="/etc/bash_completion.d"
    elif [[ -d "/usr/local/etc/bash_completion.d" ]]; then
        bash_dir="/usr/local/etc/bash_completion.d"
    elif [[ -d "/opt/homebrew/etc/bash_completion.d" ]]; then
        bash_dir="/opt/homebrew/etc/bash_completion.d"
    fi

    # Zsh (macOS Homebrew or Linux)
    local zsh_dir=""
    if [[ -d "/usr/share/zsh/site-functions" ]]; then
        zsh_dir="/usr/share/zsh/site-functions"
    elif [[ -d "/opt/homebrew/share/zsh/site-functions" ]]; then
        zsh_dir="/opt/homebrew/share/zsh/site-functions"
    elif [[ -d "/usr/local/share/zsh/site-functions" ]]; then
        zsh_dir="/usr/local/share/zsh/site-functions"
    fi

    # fish
    local fish_dir=""
    if [[ -d "/usr/share/fish/vendor_completions.d" ]]; then
        fish_dir="/usr/share/fish/vendor_completions.d"
    elif [[ -d "/opt/homebrew/share/fish/vendor_completions.d" ]]; then
        fish_dir="/opt/homebrew/share/fish/vendor_completions.d"
    elif [[ -d "/usr/local/share/fish/vendor_completions.d" ]]; then
        fish_dir="/usr/local/share/fish/vendor_completions.d"
    fi

    local ok=0
    if [[ $DO_BASH -eq 1 ]] && [[ -n "$bash_dir" ]] && [[ -f "$COMPLETION_BASH" ]]; then
        if sudo cp "$COMPLETION_BASH" "$bash_dir/nw" 2>/dev/null; then
            ok=1; print_success "Bash: $bash_dir/nw"; fi
    fi
    if [[ $DO_ZSH -eq 1 ]] && [[ -n "$zsh_dir" ]] && [[ -f "$COMPLETION_ZSH" ]]; then
        # zsh requires leading underscore for function name files
        if sudo cp "$COMPLETION_ZSH" "$zsh_dir/_nw" 2>/dev/null; then
            ok=1; print_success "Zsh: $zsh_dir/_nw"; fi
    fi
    if [[ $DO_FISH -eq 1 ]] && [[ -n "$fish_dir" ]] && [[ -f "$COMPLETION_FISH" ]]; then
        if sudo cp "$COMPLETION_FISH" "$fish_dir/nw.fish" 2>/dev/null; then
            ok=1; print_success "fish: $fish_dir/nw.fish"; fi
    fi

    if [[ $ok -eq 1 ]]; then
        print_status "System-wide installation complete. Restart your shell."
        return 0
    else
        print_warning "No suitable system completion directories found or copy failed"
        return 1
    fi
}

# Method 2: User-specific installation
install_user_specific() {
    print_status "Installing for current user..."

    # bash
    if [[ $DO_BASH -eq 1 ]] && [[ -f "$COMPLETION_BASH" ]]; then
        local bashrc="$HOME/.bashrc"
        local bash_profile="$HOME/.bash_profile"
        local profile="$HOME/.profile"
        local target_file=""
        if [[ -f "$bashrc" ]]; then target_file="$bashrc"; elif [[ -f "$bash_profile" ]]; then target_file="$bash_profile"; elif [[ -f "$profile" ]]; then target_file="$profile"; else target_file="$bashrc"; touch "$target_file"; fi
        if ! grep -q "bash_completion_nw.sh" "$target_file" 2>/dev/null; then
            {
                echo "";
                echo "# nw bash completion";
                echo "source \"$COMPLETION_BASH\"";
            } >> "$target_file"
            print_success "Bash: added source to $target_file"
        else
            print_warning "Bash completion already configured in $target_file"
        fi
    fi

    # zsh
    if [[ $DO_ZSH -eq 1 ]] && [[ -f "$COMPLETION_ZSH" ]]; then
        local zfunc_dir="$HOME/.zsh/completions"
        mkdir -p "$zfunc_dir"
        cp "$COMPLETION_ZSH" "$zfunc_dir/_nw"
        if ! grep -q "fpath+=\$HOME/.zsh/completions" "$HOME/.zshrc" 2>/dev/null; then
            echo 'fpath+=$HOME/.zsh/completions' >> "$HOME/.zshrc"
            echo 'autoload -Uz compinit && compinit' >> "$HOME/.zshrc"
        fi
        print_success "Zsh: installed to $zfunc_dir/_nw"
    fi

    # fish
    if [[ $DO_FISH -eq 1 ]] && [[ -f "$COMPLETION_FISH" ]]; then
        local fish_dir="$HOME/.config/fish/completions"
        mkdir -p "$fish_dir"
        cp "$COMPLETION_FISH" "$fish_dir/nw.fish"
        print_success "fish: installed to $fish_dir/nw.fish"
    fi

    print_status "User-specific installation complete. Restart your shell."
    return 0
}

# Method 3: Manual installation instructions
show_manual_instructions() {
    print_status "Manual installation instructions:"
    echo ""
    echo "Bash:"
    echo "  - Source directly in your shell profile:"
    echo "      source \"$COMPLETION_BASH\""
    echo "  - Or copy to a completion directory (one of):"
    echo "      sudo cp \"$COMPLETION_BASH\" /etc/bash_completion.d/nw"
    echo "      sudo cp \"$COMPLETION_BASH\" /usr/share/bash-completion/completions/nw"
    echo "      sudo cp \"$COMPLETION_BASH\" /usr/local/etc/bash_completion.d/nw"
    echo ""
    echo "Zsh:"
    echo "  - Copy to a directory in your fpath and run compinit:"
    echo "      mkdir -p ~/.zsh/completions && cp \"$COMPLETION_ZSH\" ~/.zsh/completions/_nw"
    echo "      echo 'fpath+=\$HOME/.zsh/completions' >> ~/.zshrc"
    echo "      echo 'autoload -Uz compinit && compinit' >> ~/.zshrc"
    echo ""
    echo "fish:"
    echo "  - Copy to your fish completions directory:"
    echo "      mkdir -p ~/.config/fish/completions && cp \"$COMPLETION_FISH\" ~/.config/fish/completions/nw.fish"
    echo ""
}

# Main installation logic
main() {
    print_status "nw completion installer"
    echo ""
    # Parse optional per-shell flags
    while [[ $# -gt 0 ]]; do
        case "${1:-}" in
            --bash) DO_BASH=1; DO_ZSH=0; DO_FISH=0; shift ;;
            --zsh) DO_BASH=0; DO_ZSH=1; DO_FISH=0; shift ;;
            --fish) DO_BASH=0; DO_ZSH=0; DO_FISH=1; shift ;;
            --all) DO_BASH=1; DO_ZSH=1; DO_FISH=1; shift ;;
            *) break ;;
        esac
    done

    # Check if user wants system-wide installation
    if [[ "${1:-}" == "--system" ]] || [[ "${1:-}" == "-s" ]]; then
        if install_system_wide; then
            print_status "System-wide installation done. Open a new shell to use completions."
            exit 0
        else
            print_error "System-wide installation failed"
            exit 1
        fi
    fi

    # Check if user wants user-specific installation
    if [[ "${1:-}" == "--user" ]] || [[ "${1:-}" == "-u" ]]; then
        install_user_specific
        exit 0
    fi

    # Check if user wants manual instructions only
    if [[ "${1:-}" == "--manual" ]] || [[ "${1:-}" == "-m" ]]; then
        show_manual_instructions
        exit 0
    fi

    # Default behavior: try system-wide, fall back to user-specific
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [OPTIONS] [--bash|--zsh|--fish|--all]"
        echo ""
    echo "Install shell completions for nw (bash/zsh/fish)"
        echo ""
        echo "Options:"
        echo "  -s, --system     Install system-wide (requires sudo)"
        echo "  -u, --user       Install for current user only"
        echo "  -m, --manual     Show manual installation instructions"
    echo "      --bash       Only install bash completions"
    echo "      --zsh        Only install zsh completions"
    echo "      --fish       Only install fish completions"
    echo "      --all        Install all shells (default)"
        echo "  -h, --help       Show this help message"
        echo ""
        echo "Default behavior: try system-wide, fall back to user-specific"
        exit 0
    fi

    # Try system-wide first, then user-specific
    if ! install_system_wide; then
        print_status "Falling back to user-specific installation..."
        install_user_specific
    fi

    echo ""
    print_success "Installation complete!"
    print_status "To test the completion, try:"
    echo "    nw <TAB><TAB>"
    echo ""
    print_status "If completion doesn't work immediately, try:"
    echo "    # bash only:"
    echo "    source \"$COMPLETION_BASH\""
    echo "    # or start a new bash session"
}

# Run main function with all arguments
main "$@"
