# Platform Compatibility

Networka provides comprehensive cross-platform support, ensuring network engineers can use the same powerful automation tools regardless of their operating system.

## Supported Platforms

### Operating Systems

- **Linux**: All major distributions (Ubuntu, RHEL, CentOS, Debian, etc.)
- **macOS**: Intel and Apple Silicon (M1/M2/M3) processors
- **Windows**: Windows 10/11 (x64)

### Python Versions

- **Python 3.11**: Full support
- **Python 3.12**: Full support
- **Python 3.13**: Full support

## Tested configurations

CI validates Linux, macOS, and Windows runners across Python 3.11–3.13. For production usage, Linux and macOS are first-class; Windows is best-effort unless using WSL2.

## Installation Notes

### Linux

- No additional system dependencies required
- Works with all major package managers (apt, yum, dnf, pacman)
- Container-ready for Docker deployments

## Tested configurations

CI covers Linux, macOS, and Windows runners across Python 3.11–3.13. For production usage, Linux and macOS are first-class; Windows is best-effort unless using WSL2.

- Scrapli (default transport) is not officially supported on native Windows. It may work via Paramiko or ssh2-python, but the strongly recommended setup is WSL2 (Ubuntu) to provide a POSIX environment.
- Pre-built wheels for all C extensions
- No Visual Studio Build Tools required
- PowerShell and Command Prompt compatible (best-effort); WSL2 is preferred

- Scrapli (default transport) is not officially supported on native Windows. It may work via Paramiko or ssh2-python, but the strongly recommended setup is WSL2 (Ubuntu) to provide a POSIX environment.
- PowerShell and Command Prompt are supported on a best-effort basis; prefer WSL2 for a smoother experience.

#### WSL2 quickstart (recommended)

1. Enable WSL and install Ubuntu from the Microsoft Store
2. Open Ubuntu terminal
3. Install uv and git, then install Networka from GitHub:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL
uv tool install git+https://github.com/narrowin/networka.git
nw --help
```

### Networking Libraries

- **scrapli**: Multi-vendor SSH automation

### Cryptography

- **cryptography**: Modern cryptographic recipes
- **bcrypt**: Password hashing
- **pynacl**: Networking and cryptography

### Performance

## Performance notes

Performance is comparable across Linux and macOS. On Windows, use WSL2 for best results.

- **asyncio**: Cross-platform async support

## Known Platform Differences

### Path Handling

- Automatic path normalization across platforms
- Windows drive letter support
- POSIX-style paths on Linux/macOS

### Terminal Colors

- Rich terminal support on all platforms
- Windows Terminal and PowerShell color support
- Graceful fallback for legacy terminals

### SSH Key Management

- Platform-native SSH key locations
- Windows OpenSSH integration
- macOS Keychain integration available

## Troubleshooting

### Windows-Specific Issues

If you encounter permission issues on Windows:

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS-Specific Issues

For macOS Gatekeeper warnings:

```bash
# Trust the Python installation
xattr -d com.apple.quarantine /usr/local/bin/python3
```

### Linux-Specific Issues

For older distributions, ensure Python 3.11+ is available:

```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11

# RHEL/CentOS
sudo dnf install python3.11
```

## Performance notes

Performance is comparable across Linux and macOS. On Windows, use WSL2 for best results.

## Container Support

### Docker

```dockerfile
FROM python:3.12-slim
RUN pip install git+https://github.com/narrowin/networka.git
```

### Podman

```bash
podman run -it python:3.12-slim
pip install git+https://github.com/narrowin/networka.git
```

## CI/CD Integration

Networka is tested across platforms using GitHub Actions:

- Ubuntu runners for Linux testing
- macOS runners for Apple platform testing
- Windows runners for Microsoft platform testing

This ensures every release works reliably across all supported platforms.
