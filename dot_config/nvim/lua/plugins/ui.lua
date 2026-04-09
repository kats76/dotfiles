return {
  -- Instalamos el tema Catppuccin
  {
    "catppuccin/nvim",
    name = "catppuccin",
    priority = 1000, -- Esto hace que se cargue antes que lo demás
    config = function()
      -- Cargar el tema una vez instalado
      vim.cmd.colorscheme("catppuccin-mocha")
    end,
  },

  -- También vamos a añadir iconos (necesarios para que todo se vea moderno)
  { "nvim-tree/nvim-web-devicons", lazy = true },
}
