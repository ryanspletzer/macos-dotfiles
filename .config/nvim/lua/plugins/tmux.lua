-- Seamless Neovim/tmux navigation and resize
-- Ctrl+h/j/k/l moves between Neovim splits AND tmux panes
-- Ctrl+Shift+Arrow resizes across both
return {
  "aserowy/tmux.nvim",
  event = "VeryLazy",
  opts = {
    copy_sync = {
      enable = false, -- system clipboard handles this
    },
    navigation = {
      enable_default_keybindings = true, -- Ctrl+h/j/k/l
      cycle_navigation = false, -- don't wrap around edges
      persist_zoom = false,
    },
    resize = {
      enable_default_keybindings = true, -- Ctrl+Shift+Arrow
      resize_step_x = 5,
      resize_step_y = 5,
    },
  },
}
