return {
  {
    "lukas-reineke/virt-column.nvim",
    opts = {
      char = "│",
      virtcolumn = "80,100,114,116,120",
      highlight = "VirtColumn",
    },
    config = function(_, opts)
      -- Subtle blue-gray that complements tokyonight
      vim.api.nvim_set_hl(0, "VirtColumn", { fg = "#3b4261" })
      require("virt-column").setup(opts)
    end,
  },
}
