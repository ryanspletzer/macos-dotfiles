return {
  {
    "lukas-reineke/virt-column.nvim",
    opts = {
      char = "│",
      virtcolumn = "80,100,114,116,120",
      highlight = "VirtColumn",
    },
    config = function(_, opts)
      -- Subtle gray that complements vscode.nvim Dark Modern
      vim.api.nvim_set_hl(0, "VirtColumn", { fg = "#333333" })
      require("virt-column").setup(opts)
    end,
  },
}
