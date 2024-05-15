export GPG_TTY=$(tty)

if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init bash --config ~/.oh-my-posh/themes/mytheme.json)"
fi

alias cls=clear
alias openremote='open $(git remote get-url origin)'

source $(brew --prefix)/opt/chruby/share/chruby/chruby.sh
source $(brew --prefix)/opt/chruby/share/chruby/auto.sh
chruby ruby-3.1.3

alias pwsh='pwsh -NoLogo'
alias finder='open -a finder'

[ -f ~/.fzf.bash ] && source ~/.fzf.bash
. "$HOME/.cargo/env"

eval "$(direnv hook bash)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# For pipx
export PATH=$PATH:~/.local/bin

