. "$HOME/.cargo/env"

# Machine-specific overrides, selected by home directory
# (shell analogue of the gitignored ~/.gitconfig.local)
case "$HOME" in
  /Users/spletzr)   [[ -f "$HOME/.zshenv.work" ]]     && . "$HOME/.zshenv.work" ;;
  /Users/rspletzer) [[ -f "$HOME/.zshenv.personal" ]] && . "$HOME/.zshenv.personal" ;;
esac
