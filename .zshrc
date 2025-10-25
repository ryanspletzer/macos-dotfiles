export GPG_TTY=$(tty)

source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source $(brew --prefix)/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh
zstyle ':autocomplete:*' ignored-input '..##'
#source /opt/homebrew/share/zsh-history-substring-search/zsh-history-substring-search.zsh
#bindkey '^[[A' history-substring-search-up
#bindkey '^[[B' history-substring-search-down
source $(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh

if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init zsh --config ~/.oh-my-posh/themes/mytheme.json)"
fi

autoload -Uz compinit && compinit

alias cls=clear
alias openremote='open $(git remote get-url origin)'

source $(brew --prefix)/opt/chruby/share/chruby/chruby.sh
source $(brew --prefix)/opt/chruby/share/chruby/auto.sh
chruby ruby-3.4.1

alias pwsh='pwsh -NoLogo'
alias finder='open -a finder'

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

eval "$(direnv hook zsh)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# For pipx
export PATH=$PATH:~/.local/bin

export NVM_DIR="$HOME/.nvm"
[ -s "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" ] && \. "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" # This loads nvm
[ -s "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm"
