eval "$(/opt/homebrew/bin/brew shellenv)"
export GPG_TTY=$(tty)

# Autodesk Artifactory npm token (from Keychain)
set -l _npm_token (security find-generic-password \
  -s npm-autodesk-token -w 2>/dev/null)
and set -gx NPM_AUTODESK_TOKEN $_npm_token

if test "$TERM_PROGRAM" != "Apple_Terminal"
    oh-my-posh init fish --config ~/.oh-my-posh/themes/mytheme.yaml | source
end

alias cls=clear
alias cat='bat --paging=never'
alias ls='eza --icons'
alias ll='eza -la --icons --git'
alias lt='eza --tree --level=2 --icons'
alias openremote='open $(git remote get-url origin)'
set -gx MANPAGER "sh -c 'col -bx | bat -l man -p'"

chruby ruby-3.4.1

alias pwsh='pwsh -NoLogo'
alias finder='open -a finder'
function emacsd
    emacs $argv &
    disown
end

alias gd='git diff'
alias gdc='git diff --color=always'
alias gs='git status'
alias gsc='git -c color.status=always status'

set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
set -gx FZF_CTRL_T_OPTS "--preview 'bat -n --color=always {}'"
set -gx FZF_ALT_C_OPTS "--preview 'eza --tree --level=2 --icons --color=always {}'"

zoxide init fish | source
direnv hook fish | source
pyenv init - | source

if status is-interactive
    pyenv virtualenv-init - | source
end

function sync_git_remote
    argparse 'b=' 'f' -- $argv
    or return 1

    set -l branch $_flag_b
    set -l force $_flag_f

    set -l current_branch (git branch --show-current 2>/dev/null)
    or return 1

    if test -z "$current_branch"
        echo "No current branch detected." >&2
        return 1
    end

    if git remote get-url upstream >/dev/null 2>&1
        set -l pull_remote upstream
    else
        set -l pull_remote origin
    end

    set -l trunk ""
    if not string match -qr '^(main|master)$' "$current_branch"
        if git branch --list main | string length -q
            set trunk main
        else
            set trunk master
        end
        git checkout "$trunk"
        or return $status
        if test -n "$force"
            git branch -D "$current_branch"
            or return $status
        end
    else
        if git branch --list main | string length -q
            set trunk main
        else
            set trunk master
        end
    end

    if test -z "$trunk"
        echo "Unable to determine trunk branch." >&2
        return 1
    end

    git pull $pull_remote "$trunk"
    or return $status
    if test "$pull_remote" = upstream
        git push
        or return $status
    end
    git remote prune origin
    or return $status

    if test -n "$branch"
        git branch -D "$branch"
        or return $status
    end
end
alias syncremote=sync_git_remote

function open_textedit
    set -l file_path $argv[1]

    if test -z "$file_path"
        echo "File path required" >&2
        return 1
    end

    if test -e "$file_path"
        set -l resolved_path (realpath "$file_path" 2>/dev/null)
        or set resolved_path "$file_path"
    else
        echo "File not found: $file_path" >&2
        return 1
    end

    open -a TextEdit "$resolved_path"
end
alias textedit=open_textedit

function start_caffeination
    argparse 's' -- $argv
    or return 1

    if set -q _flag_s
        open -a /System/Library/CoreServices/ScreenSaverEngine.app
    end

    caffeinate -disu
end
alias caf=start_caffeination

function code --wraps code --description 'Launch VS Code with selective extensions'
    set -l project_dir ""
    for arg in $argv
        if test -d "$arg"
            set project_dir "$arg"
            break
        end
    end
    if test -z "$project_dir"
        set project_dir "."
    end

    set -l extensions_json "$project_dir/.vscode/extensions.json"

    if not test -f "$extensions_json"; or not command -sq jq
        command code $argv
        return
    end

    set -l wanted (jq -r '.recommendations[]' "$extensions_json" | tr '[:upper:]' '[:lower:]')
    set -l disable_flags

    for ext in (command code --list-extensions)
        set -l ext_lower (string lower "$ext")
        if not contains "$ext_lower" $wanted
            set -a disable_flags --disable-extension $ext
        end
    end

    # Warn if any recommended extension is manually disabled in workspace storage
    if command -sq sqlite3
        set -l abs_dir (builtin cd "$project_dir" && pwd)
        set -l folder_uri "file://$abs_dir"
        set -l storage_base "$HOME/Library/Application Support/Code/User/workspaceStorage"
        if test -d "$storage_base"
            for ws_dir in "$storage_base"/*/
                set -l ws_json "$ws_dir/workspace.json"
                test -f "$ws_json"; or continue
                set -l ws_folder (jq -r '.folder // empty' "$ws_json" 2>/dev/null)
                if test "$ws_folder" = "$folder_uri"
                    set -l db "$ws_dir/state.vscdb"
                    test -f "$db"; or break
                    set -l disabled_json (sqlite3 "$db" \
                        "SELECT value FROM ItemTable WHERE key = 'extensionsIdentifiers/disabled';" 2>/dev/null)
                    if test -z "$disabled_json"; or test "$disabled_json" = "[]"
                        break
                    end
                    for w in $wanted
                        if echo "$disabled_json" | jq -e --arg id "$w" \
                            'map(select(.id | ascii_downcase == $id)) | length > 0' &>/dev/null
                            echo "WARNING: extension '$w' is recommended but manually disabled in VS Code workspace storage." >&2
                            echo "  Fix: open VS Code, re-enable it, or clear workspace storage state." >&2
                        end
                    end
                    break
                end
            end
        end
    end

    command code $disable_flags $argv
end
