return {
  -- Treesitter syntax highlighting
  {
    "nvim-treesitter/nvim-treesitter",
    opts = { ensure_installed = { "powershell" } },
  },
  -- LSP via PowerShell Editor Services
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        powershell_es = {},
      },
    },
  },
  -- Auto-install PSES via Mason
  {
    "mason-org/mason.nvim",
    opts = { ensure_installed = { "powershell-editor-services" } },
  },
}
