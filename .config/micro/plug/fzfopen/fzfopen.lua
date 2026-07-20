VERSION = "1.0.0"

-- VS Code-style Ctrl+P quick open, backed by fzf.
-- Bound in bindings.json as lua:fzfopen.fzfOpen; also available as `> fzf`.

local config = import("micro/config")
local shell = import("micro/shell")

function fzfOpen(bp)
    local output, err = shell.RunInteractiveShell("fzf", false, true)
    -- err is non-nil when fzf is cancelled (Esc / Ctrl-C); treat as a no-op
    if err == nil then
        local filepath = output:gsub("[\n\r]", "")
        if filepath ~= "" then
            bp:HandleCommand(string.format("open %q", filepath))
        end
    end
end

function init()
    config.MakeCommand("fzf", fzfOpen, config.NoComplete)
end
