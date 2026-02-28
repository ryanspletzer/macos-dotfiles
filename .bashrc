export GPG_TTY=$(tty)

# Autodesk Artifactory npm token (from Keychain)
NPM_AUTODESK_TOKEN="$(security find-generic-password \
  -s npm-autodesk-token -w 2>/dev/null)" && \
  export NPM_AUTODESK_TOKEN

if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init bash --config ~/.oh-my-posh/themes/mytheme.yaml)"
fi

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
eval "$(fzf --bash)"
. "$HOME/.cargo/env"

eval "$(zoxide init bash)"
eval "$(direnv hook bash)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# For pipx
export PATH=$PATH:~/.local/bin

export NVM_DIR="$HOME/.nvm"
[ -s "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" ] && \. "$HOMEBREW_PREFIX/opt/nvm/nvm.sh" # This loads nvm
[ -s "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm"

sync_git_remote() {
    local OPTIND=1 opt branch force current_branch trunk pull_remote
    branch=""
    force=false

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
        if git branch --list main | grep -q .; then
            trunk=main
        else
            trunk=master
        fi
        git checkout "$trunk" || return $?
        if [[ $force == true ]]; then
            git branch -D "$current_branch" || return $?
        fi
    else
        if git branch --list main | grep -q .; then
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
    mapfile -t wanted < <(
        jq -r '.recommendations[]' "$extensions_json" | tr '[:upper:]' '[:lower:]'
    )

    while IFS= read -r ext; do
        local ext_lower="${ext,,}"
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

    # Warn if any recommended extension is manually disabled in workspace storage
    if command -v sqlite3 &>/dev/null; then
        local abs_dir
        abs_dir="$(cd "$project_dir" && pwd)"
        local folder_uri="file://$abs_dir"
        local storage_base="$HOME/Library/Application Support/Code/User/workspaceStorage"
        if [[ -d "$storage_base" ]]; then
            for ws_dir in "$storage_base"/*/; do
                local ws_json="$ws_dir/workspace.json"
                [[ -f "$ws_json" ]] || continue
                local ws_folder
                ws_folder="$(jq -r '.folder // empty' "$ws_json" 2>/dev/null)"
                if [[ "$ws_folder" == "$folder_uri" ]]; then
                    local db="$ws_dir/state.vscdb"
                    [[ -f "$db" ]] || break
                    local disabled_json
                    disabled_json="$(sqlite3 "$db" \
                        "SELECT value FROM ItemTable WHERE key = 'extensionsIdentifiers/disabled';" 2>/dev/null)"
                    [[ -z "$disabled_json" || "$disabled_json" == "[]" ]] && break
                    for w in "${wanted[@]}"; do
                        if echo "$disabled_json" | jq -e --arg id "$w" \
                            'map(select(.id | ascii_downcase == $id)) | length > 0' &>/dev/null; then
                            echo "WARNING: extension '$w' is recommended but manually disabled in VS Code workspace storage." >&2
                            echo "  Fix: open VS Code, re-enable it, or clear workspace storage state." >&2
                        fi
                    done
                    break
                fi
            done
        fi
    fi

    command code "${disable_flags[@]}" "$@"
}
