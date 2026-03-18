. "$HOME/.cargo/env"

# Machine-specific overrides (mirrors .gitconfig.work / .gitconfig.personal pattern)
case "$HOME" in
  /Users/spletzr)   [[ -f "$HOME/.zshenv.work" ]]     && . "$HOME/.zshenv.work" ;;
  /Users/rspletzer) [[ -f "$HOME/.zshenv.personal" ]] && . "$HOME/.zshenv.personal" ;;
esac
