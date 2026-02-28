export GPG_TTY=$(tty)

# Autodesk Artifactory npm token (from Keychain)
NPM_AUTODESK_TOKEN="$(security find-generic-password \
  -s npm-autodesk-token -w 2>/dev/null)" && \
  export NPM_AUTODESK_TOKEN

# ngrok auth token (from KeyChain)
NGROK_AUTHTOKEN="$(security find-generic-password \
  -s ngrok -a authtoken -w 2>/dev/null)" && \
  export NGROK_AUTHTOKEN

source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source $(brew --prefix)/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh
zstyle ':autocomplete:*' ignored-input '..##'
source $(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh

if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init zsh --config ~/.oh-my-posh/themes/mytheme.yaml)"
fi

# Bind Shift+Enter escape sequences to accept-line so they act like Enter
# (Ghostty sends these modified key sequences; zsh doesn't recognize them by default)
bindkey '\e[27;2;13~' accept-line  # xterm modifyOtherKeys format
bindkey '\e[13;2u' accept-line     # CSI u / kitty format (used by tmux extended-keys)

autoload -Uz compinit && compinit

alias cls=clear
alias cat='bat --paging=never'
alias ls='eza --icons'
alias ll='eza -la --icons --git'
alias lt='eza --tree --level=2 --icons'
alias openremote='open $(git remote get-url origin)'
export MANPAGER="sh -c 'col -bx | bat -l man -p'"

source $(brew --prefix)/opt/chruby/share/chruby/chruby.sh
source $(brew --prefix)/opt/chruby/share/chruby/auto.sh
chruby ruby-3.4.1

alias pwsh='pwsh -NoLogo'
alias finder='open -a finder'
alias emacsd='emacs & disown'

alias gd='git diff'
alias gdc='git diff --color=always'
alias gs='git status'
alias gsc='git -c color.status=always status'

export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_CTRL_T_OPTS="--preview 'bat -n --color=always {}'"
export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --icons --color=always {}'"
source <(fzf --zsh)

eval "$(zoxide init zsh)"
eval "$(direnv hook zsh)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# For pipx
export PATH=$PATH:~/.local/bin

export NVM_DIR="$HOME/.nvm"
[ -s "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" ] && \. "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" # This loads nvm
[ -s "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm"

sync_git_remote() {
    local OPTIND=1 opt branch="" force=false current_branch trunk="" pull_remote
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

    if git remote get-url upstream >/dev/null 2>&1; then
        pull_remote=upstream
    else
        pull_remote=origin
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

    git pull "$pull_remote" "$trunk" || return $?
    if [[ $pull_remote == upstream ]]; then
        git push || return $?
    fi
    git remote prune origin || return $?

    if [[ -n $branch ]]; then
        git branch -D "$branch" || return $?
    fi
}
alias syncremote=sync_git_remote

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

code() {
    local project_dir=""
    for arg in "$@"; do
        if [[ -d "$arg" ]]; then
            project_dir="$arg"
            break
        fi
    done
    [[ -z "$project_dir" ]] && project_dir="."

    local extensions_json="$project_dir/.vscode/extensions.json"

    if [[ ! -f "$extensions_json" ]] || ! command -v jq &>/dev/null; then
        command code "$@"
        return
    fi

    local -a wanted disable_flags
    wanted=("${(@f)$(jq -r '.recommendations[]' "$extensions_json" | tr '[:upper:]' '[:lower:]')}")

    while IFS= read -r ext; do
        local ext_lower="${ext:l}"
        local match=false
        for w in "${wanted[@]}"; do
            if [[ "$ext_lower" == "$w" ]]; then
                match=true
                break
            fi
        done
        if [[ "$match" == false ]]; then
            disable_flags+=("--disable-extension" "$ext")
        fi
    done < <(command code --list-extensions)

    command code "${disable_flags[@]}" "$@"
}

restart_globalprotect() {
    local gui_target="gui/$(id -u)"
    local pangpa_label="com.paloaltonetworks.gp.pangpa"
    local pangps_label="com.paloaltonetworks.gp.pangps"
    local pangpa_plist="/Library/LaunchAgents/com.paloaltonetworks.gp.pangpa.plist"
    local pangps_plist="/Library/LaunchAgents/com.paloaltonetworks.gp.pangps.plist"

    echo "Restarting GlobalProtect..."

    # Stop services (only if loaded)
    if launchctl list "$pangpa_label" &>/dev/null; then
        echo "  Stopping $pangpa_label..."
        sudo launchctl bootout "$gui_target" "$pangpa_plist" 2>/dev/null
    else
        echo "  $pangpa_label not loaded, skipping stop"
    fi

    if launchctl list "$pangps_label" &>/dev/null; then
        echo "  Stopping $pangps_label..."
        sudo launchctl bootout "$gui_target" "$pangps_plist" 2>/dev/null
    else
        echo "  $pangps_label not loaded, skipping stop"
    fi

    # Kill lingering processes (only if running)
    for proc in PanGPA PanGPS GlobalProtect; do
        if pgrep -x "$proc" &>/dev/null; then
            echo "  Killing $proc process..."
            sudo pkill -x "$proc" 2>/dev/null
        fi
    done

    echo "  Waiting for cleanup..."
    sleep 2

    # Start services (only if not already loaded)
    if ! launchctl list "$pangps_label" &>/dev/null; then
        echo "  Starting $pangps_label..."
        sudo launchctl bootstrap "$gui_target" "$pangps_plist"
    else
        echo "  $pangps_label already running"
    fi

    if ! launchctl list "$pangpa_label" &>/dev/null; then
        echo "  Starting $pangpa_label..."
        sudo launchctl bootstrap "$gui_target" "$pangpa_plist"
    else
        echo "  $pangpa_label already running"
    fi

    echo "  Waiting for services to initialize..."
    sleep 2

    # Open app (only if not running)
    if ! pgrep -x "GlobalProtect" &>/dev/null; then
        echo "  Opening GlobalProtect app..."
        open -a /Applications/GlobalProtect.app
    else
        echo "  GlobalProtect app already running"
    fi

    echo "GlobalProtect restart complete."
}
