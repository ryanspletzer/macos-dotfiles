eval "$(/opt/homebrew/bin/brew shellenv)"
export GPG_TTY=$(tty)
if test "$TERM_PROGRAM" != "Apple_Terminal"
    oh-my-posh init fish --config ~/.oh-my-posh/themes/mytheme.json | source
end

alias cls=clear
alias openremote='open $(git remote get-url origin)'

chruby ruby-3.4.1

alias pwsh='pwsh -NoLogo'
alias finder='open -a finder'

pyenv init - | source

if status is-interactive
    pyenv virtualenv-init - | source
end
