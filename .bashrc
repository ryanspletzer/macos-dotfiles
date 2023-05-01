export GPG_TTY=$(tty)

if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init bash --config ~/.oh-my-posh/themes/mytheme.json)"
fi

alias cls=clear
alias openremote='open $(git remote get-url origin)'

source /opt/homebrew/opt/chruby/share/chruby/chruby.sh
source /opt/homebrew/opt/chruby/share/chruby/auto.sh
chruby ruby-3.1.3

alias pwsh='pwsh -NoLogo'
