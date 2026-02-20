-- Show hidden files/directories by default in mini.files
return {
  "echasnovski/mini.files",
  opts = {
    content = {
      filter = function()
        return true
      end,
    },
  },
}
