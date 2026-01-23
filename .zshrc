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

sync_git_origin_remote_from_upstream() {
    local OPTIND=1 opt branch="" force=false current_branch trunk=""
    while getopts ":b:f" opt; do
        case $opt in
            b) branch=$OPTARG ;;
            f) force=true ;;
        esac
    done
    shift $((OPTIND - 1))

    current_branch=$(git branch --show-current 2>/dev/null) || return 1
    if [[ -z $current_branch ]]; then
        echo "No current branch detected." >&2
        return 1
    fi

    if ! git remote get-url upstream >/dev/null 2>&1; then
        echo "Missing 'upstream' remote." >&2
        return 1
    fi

    if [[ ! $current_branch =~ ^(main|master)$ ]]; then
        if git branch --list main >/dev/null 2>&1; then
            trunk=main
        else
            trunk=master
        fi
        git checkout "$trunk" || return $?
        if [[ $force == true ]]; then
            git branch -D "$current_branch" || return $?
        fi
    else
        if git branch --list main >/dev/null 2>&1; then
            trunk=main
        else
            trunk=master
        fi
    fi

    if [[ -z $trunk ]]; then
        echo "Unable to determine trunk branch." >&2
        return 1
    fi

    git pull upstream "$trunk" || return $?
    git push || return $?
    git remote prune origin || return $?

    if [[ -n $branch ]]; then
        git branch -D "$branch" || return $?
    fi
}
alias syncremote=sync_git_origin_remote_from_upstream

open_textedit() {
    local file_path="$1"
    local resolved_path

    if [[ -z "$file_path" ]]; then
        echo "File path required" >&2
        return 1
    fi

    if [[ -e "$file_path" ]]; then
        resolved_path=$(realpath "$file_path" 2>/dev/null) || resolved_path="$file_path"
    else
        echo "File not found: $file_path" >&2
        return 1
    fi

    open -a TextEdit "$resolved_path"
}
alias textedit=open_textedit

start_caffeination() {
    local OPTIND=1 opt screensaver=false

    while getopts ":s" opt; do
        case $opt in
            s) screensaver=true ;;
        esac
    done
    shift $((OPTIND - 1))

    if [[ $screensaver == true ]]; then
        open -a /System/Library/CoreServices/ScreenSaverEngine.app
    fi

    caffeinate -disu
}
alias caf=start_caffeination
