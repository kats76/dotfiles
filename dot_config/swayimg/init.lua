-- Visor de imágenes con la paleta de Hyprland (colores en formato 0xAARRGGBB)
-- Solo se cambia el aspecto: atajos y comportamiento son los de serie

-- Texto (nombre, tamaño, zoom...)
swayimg.text.font = "JetBrainsMono Nerd Font"
swayimg.text.size = 18
swayimg.text.color = 0xffcdd6f4      -- fg
swayimg.text.background = 0xcc1e1e2e -- bg al 80 %
swayimg.text.shadow = 0x00000000

-- Visor y presentación
swayimg.viewer.set_window_background(0xff1e1e2e)
swayimg.viewer.set_image_chessboard(20, 0xff252536, 0xff313244)
swayimg.viewer.mark_color = 0xff8a63c7
swayimg.slideshow.set_window_background(0xff1e1e2e)

-- Galería de miniaturas
swayimg.gallery.window_color = 0xff1e1e2e
swayimg.gallery.unselected_color = 0xff252536
swayimg.gallery.selected_color = 0xff313244
swayimg.gallery.border_color = 0xff8a63c7 -- accent
swayimg.gallery.border_size = 3
swayimg.gallery.mark_color = 0xff6f9f98
