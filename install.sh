#!/usr/bin/env bash
# Puts `cli` on your PATH for bash and zsh. Run once per machine:
#   bash install.sh

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.local/bin"

mkdir -p "$TARGET"
chmod +x "$REPO/bin/cli"
ln -sf "$REPO/bin/cli" "$TARGET/cli"
echo "linked $TARGET/cli -> $REPO/bin/cli"

case ":$PATH:" in
  *":$TARGET:"*) ;;
  *)
    echo
    echo "$TARGET is not on your PATH. Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac

if ! command -v jq >/dev/null 2>&1; then
  echo
  echo "jq is missing. Mac: brew install jq. Windows: scoop install jq."
fi
