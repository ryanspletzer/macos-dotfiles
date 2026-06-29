eval "$(/opt/homebrew/bin/brew shellenv)"
fish_add_path --append ~/.dotnet/tools
fish_add_path --append ~/.cargo/bin
fish_add_path --append ~/.local/bin
set -gx PNPM_HOME "$HOME/Library/pnpm"
fish_add_path $PNPM_HOME/bin
set -gx BUN_INSTALL "$HOME/.bun"
fish_add_path $BUN_INSTALL/bin
export GPG_TTY=$(tty)

# Autodesk Artifactory npm token (from Keychain)
set -l _npm_token (security find-generic-password \
  -s npm-autodesk-token -w 2>/dev/null)
and set -gx NPM_AUTODESK_TOKEN $_npm_token

# ngrok auth token (from Keychain)
set -l _ngrok_token (security find-generic-password \
  -s ngrok -a authtoken -w 2>/dev/null)
and set -gx NGROK_AUTHTOKEN $_ngrok_token

if test "$TERM_PROGRAM" != "Apple_Terminal"
    oh-my-posh init fish --config ~/.oh-my-posh/themes/mytheme.yaml | source
end

# Bind Shift+Enter escape sequences to accept the line like Enter
# (Ghostty sends these modified key sequences).
function fish_user_key_bindings
    bind \e\[27\;2\;13~ "commandline -f execute"  # xterm modifyOtherKeys
    bind \e\[13\;2u "commandline -f execute"       # CSI u / kitty format
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
function emacsd  # standalone GUI Emacs
    emacs $argv &
    disown
end

function ec  # GUI frame on the Emacs daemon (starts it if needed)
    emacsclient -c -n -a "" $argv
end

function et  # terminal frame on the Emacs daemon
    emacsclient -t -a "" $argv
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
fzf --fish | source
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

function restart_globalprotect
    set -l gui_target "gui/"(id -u)
    set -l pangpa_label com.paloaltonetworks.gp.pangpa
    set -l pangps_label com.paloaltonetworks.gp.pangps
    set -l pangpa_plist /Library/LaunchAgents/com.paloaltonetworks.gp.pangpa.plist
    set -l pangps_plist /Library/LaunchAgents/com.paloaltonetworks.gp.pangps.plist

    echo "Restarting GlobalProtect..."

    # Stop services (only if loaded)
    if launchctl list "$pangpa_label" >/dev/null 2>&1
        echo "  Stopping $pangpa_label..."
        sudo launchctl bootout "$gui_target" "$pangpa_plist" 2>/dev/null
    else
        echo "  $pangpa_label not loaded, skipping stop"
    end

    if launchctl list "$pangps_label" >/dev/null 2>&1
        echo "  Stopping $pangps_label..."
        sudo launchctl bootout "$gui_target" "$pangps_plist" 2>/dev/null
    else
        echo "  $pangps_label not loaded, skipping stop"
    end

    # Kill lingering processes (only if running)
    for proc in PanGPA PanGPS GlobalProtect
        if pgrep -x "$proc" >/dev/null 2>&1
            echo "  Killing $proc process..."
            sudo pkill -x "$proc" 2>/dev/null
        end
    end

    echo "  Waiting for cleanup..."
    sleep 2

    # Start services (only if not already loaded)
    if not launchctl list "$pangps_label" >/dev/null 2>&1
        echo "  Starting $pangps_label..."
        sudo launchctl bootstrap "$gui_target" "$pangps_plist"
    else
        echo "  $pangps_label already running"
    end

    if not launchctl list "$pangpa_label" >/dev/null 2>&1
        echo "  Starting $pangpa_label..."
        sudo launchctl bootstrap "$gui_target" "$pangpa_plist"
    else
        echo "  $pangpa_label already running"
    end

    echo "  Waiting for services to initialize..."
    sleep 2

    # Open app (only if not running)
    if not pgrep -x "GlobalProtect" >/dev/null 2>&1
        echo "  Opening GlobalProtect app..."
        open -a /Applications/GlobalProtect.app
    else
        echo "  GlobalProtect app already running"
    end

    echo "GlobalProtect restart complete."
end
