# bash-completion
if [ -f /opt/local/etc/profile.d/bash_completion.sh ]; then
    . /opt/local/etc/profile.d/bash_completion.sh
fi

eval "$(/opt/homebrew/bin/brew shellenv)"
. "$HOME/.cargo/env"

# For pipx
export PATH=$PATH:~/.local/bin
