eval "$(/opt/homebrew/bin/brew shellenv)"
. "$HOME/.cargo/env"

# bash-completion (Homebrew; install with: brew install bash-completion@2)
if [ -r "${HOMEBREW_PREFIX}/etc/profile.d/bash_completion.sh" ]; then
    . "${HOMEBREW_PREFIX}/etc/profile.d/bash_completion.sh"
fi

# For pipx
export PATH=$PATH:~/.local/bin

# For .NET tools
export PATH=$PATH:~/.dotnet/tools

# Load interactive config for login shells. Unlike zsh (which always reads
# .zshrc for interactive shells), bash does not source .bashrc for login
# shells automatically, so aliases/functions/tools defined there would be
# missing from a login bash without this.
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"
