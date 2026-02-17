return {
  -- Treesitter syntax highlighting for bash/sh/zsh and fish
  {
    "nvim-treesitter/nvim-treesitter",
    opts = { ensure_installed = { "bash", "fish" } },
  },
  -- LSP via bash-language-server (covers bash, sh, zsh)
  -- Automatically uses shellcheck for diagnostics and shfmt for formatting
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        bashls = {},
      },
    },
  },
  -- Auto-install tools via Mason
  {
    "mason-org/mason.nvim",
    opts = { ensure_installed = { "bash-language-server", "shellcheck", "shfmt" } },
  },
  -- Formatting: shfmt for bash/sh/zsh, fish_indent for fish
  {
    "stevearc/conform.nvim",
    optional = true,
    opts = {
      formatters_by_ft = {
        sh = { "shfmt" },
        bash = { "shfmt" },
        zsh = { "shfmt" },
        fish = { "fish_indent" },
      },
    },
  },
}
