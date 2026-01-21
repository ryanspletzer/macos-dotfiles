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

function sync_git_origin_remote_from_upstream
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

    if not git remote get-url upstream >/dev/null 2>&1
        echo "Missing 'upstream' remote." >&2
        return 1
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

    git pull upstream "$trunk"
    or return $status
    git push
    or return $status
    git remote prune origin
    or return $status

    if test -n "$branch"
        git branch -D "$branch"
        or return $status
    end
end
alias syncremote=sync_git_origin_remote_from_upstream

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
    caffeinate -isu
end
alias caf=start_caffeination
