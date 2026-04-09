-- Usamos la API de Neovim 'vim.opt' que es la forma moderna de configurar
-- Equivale al comando ':set' de Vim.

local opt = vim.opt

-- --- APARIENCIA Y UI ---
opt.number = true           -- Muestra el número de línea actual.
opt.relativenumber = true   -- Muestra números relativos (ayuda a saltar líneas rápido).
opt.cursorline = true       -- Resalta la línea donde está el cursor.
opt.termguicolors = true    -- Habilita colores de 24 bits (indispensable para temas modernos).
opt.signcolumn = "yes"      -- Siempre reserva espacio para iconos de errores/Git (evita saltos visuales).
opt.scrolloff = 10          -- Mantiene 10 líneas visibles arriba/abajo al hacer scroll.

-- --- TABULACIÓN Y SANGRÍA ---
opt.expandtab = true        -- Transforma los tabs en espacios.
opt.shiftwidth = 2          -- Tamaño de la sangría (común en Lua/JS es 2 o 4).
opt.tabstop = 2             -- Cuántos espacios ocupa un tab visualmente.
opt.smartindent = true      -- Sangría inteligente al abrir nuevas llaves o bloques.

-- --- COMPORTAMIENTO ---
opt.ignorecase = true       -- Ignora mayúsculas al buscar...
opt.smartcase = true        -- ...a menos que escribas una mayúscula explícitamente.
opt.mouse = "a"             -- Habilita el ratón para redimensionar, scrollear y seleccionar.
opt.clipboard = "unnamedplus" -- Sincroniza el portapapeles de Neovim con el de tu sistema.
opt.updatetime = 250        -- Reduce el tiempo de espera para que se disparen eventos (más fluido).
opt.undofile = true         -- Guarda el historial de "deshacer" incluso después de cerrar el archivo.

-- --- OTROS ---
opt.splitright = true       -- Al dividir verticalmente, la nueva ventana se abre a la derecha.
opt.splitbelow = true       -- Al dividir horizontalmente, la nueva ventana se abre abajo.
