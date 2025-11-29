#!/bin/bash
# Memora one-command installer — fully local, zero tracking
set -e

REPO="https://github.com/LHMisme420/https-github.com-LHMisme420-memora.git"
INSTALL_DIR="$HOME/.memora"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"

echo "🚀 Installing Memora — your lifelong second brain (100% local, no cloud ever)"
echo

# Create install dir
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone or update
if [ -d ".git" ]; then
    echo "Updating existing Memora install..."
    git pull
else
    echo "Cloning Memora..."
    git clone "$REPO" .
fi

# Create venv
echo "Setting up Python virtual environment..."
python3 -m venv "$VENV_DIR" 2>/dev/null || python -m venv "$VENV_DIR"

# Upgrade pip & install requirements
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r requirements.txt

# Create bin dir if needed
mkdir -p "$BIN_DIR"

# Create global memora command
cat > "$BIN_DIR/memora" << 'EOF'
#!/bin/bash
exec "$HOME/.memora/venv/bin/python" "$HOME/.memora/memora.py" "$@"
EOF
chmod +x "$BIN_DIR/memora"

# Add ~/.local/bin to PATH if not needed
if ! grep -q '$HOME/.local/bin' <<< "$PATH"; then
    SHELL_RC="$HOME/.bashrc"
    [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    export PATH="$HOME/.local/bin:$PATH"
    echo "Added ~/.local/bin to your PATH (will be permanent next time you open terminal)"
fi

echo
echo "🎉 Memora is now installed!"
echo
echo "Just type:  memora"
echo "           memora recall \"what did I say about milk\""
echo "           memora stop"
echo
echo "Star the repo if this blows your mind ❤️"
echo "https://github.com/LHMisme420/https-github.com-LHMisme420-memora"
