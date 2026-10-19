"""
PyClean Pro - Módulo de Gráficas y Visualización (Charts)
Componentes gráficos nativos en modo oscuro creados con Tkinter Canvas.
No requiere dependencias externas como matplotlib.
"""

import math
import tkinter as tk
from tkinter import ttk


class DonutChart(tk.Frame):
    """
    Gráfico circular tipo Donut/Anillo moderno dibujado en Tkinter Canvas.
    Soporta múltiples segmentos de datos, texto central y leyenda inferior.
    """
    def __init__(self, parent, size=180, inner_ratio=0.65, bg_color="#1B1E2B", **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.size = size
        self.inner_ratio = inner_ratio
        self.bg_color = bg_color

        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg=self.bg_color,
            highlightthickness=0
        )
        self.canvas.pack(pady=(4, 6))

        self.legend_frame = tk.Frame(self, bg=self.bg_color)
        self.legend_frame.pack(fill=tk.X, padx=4)

        self.center_title = "0%"
        self.center_subtitle = "Sin datos"
        self.segments = []
        self.draw()

    def set_data(self, segments, center_title="", center_subtitle=""):
        """
        segments: lista de diccionarios con formato:
        [{'value': 100, 'color': '#3B82F6', 'label': 'Usado', 'text_val': '100 GB'}, ...]
        """
        self.segments = segments
        self.center_title = center_title
        self.center_subtitle = center_subtitle
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        pad = 8
        cx = self.size / 2
        cy = self.size / 2
        r_outer = (self.size / 2) - pad
        r_inner = r_outer * self.inner_ratio

        total_value = sum(s["value"] for s in self.segments if s.get("value", 0) > 0)

        # Si no hay datos o el total es 0, dibujar anillo vacío
        if total_value <= 0:
            self.canvas.create_oval(
                cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                fill="#2B3045", outline=""
            )
            self.canvas.create_oval(
                cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
                fill=self.bg_color, outline=""
            )
            self.canvas.create_text(
                cx, cy, text="Sin datos", fill="#6B7280", font=("Segoe UI", 9, "bold")
            )
            return

        current_angle = 90.0  # Empezar arriba (12 en punto)

        # Dibujar cada segmento del anillo
        for seg in self.segments:
            val = seg.get("value", 0)
            if val <= 0:
                continue
            extent = (val / total_value) * 360.0

            # Tkinter create_arc dibuja en sentido antihorario
            self.canvas.create_arc(
                cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                start=current_angle,
                extent=-extent,
                fill=seg.get("color", "#3B82F6"),
                outline=self.bg_color,
                width=1,
                style=tk.PIESLICE
            )
            current_angle -= extent

        # Recorte central para formar el donut
        self.canvas.create_oval(
            cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
            fill=self.bg_color, outline=""
        )

        # Texto central
        if self.center_title:
            self.canvas.create_text(
                cx, cy - 7,
                text=self.center_title,
                fill="#F9FAFB",
                font=("Segoe UI", 14, "bold")
            )
        if self.center_subtitle:
            self.canvas.create_text(
                cx, cy + 13,
                text=self.center_subtitle,
                fill="#9CA3AF",
                font=("Segoe UI", 8)
            )

        # Leyenda inferior
        for seg in self.segments:
            row = tk.Frame(self.legend_frame, bg=self.bg_color)
            row.pack(fill=tk.X, pady=1)

            # Punto de color
            dot = tk.Canvas(row, width=10, height=10, bg=self.bg_color, highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=(0, 5))
            dot.create_oval(1, 1, 9, 9, fill=seg.get("color", "#3B82F6"), outline="")

            # Etiqueta
            lbl = tk.Label(
                row,
                text=seg.get("label", ""),
                font=("Segoe UI", 8),
                bg=self.bg_color,
                fg="#D1D5DB"
            )
            lbl.pack(side=tk.LEFT)

            # Valor formateado
            val_lbl = tk.Label(
                row,
                text=seg.get("text_val", ""),
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_color,
                fg="#F3F4F6"
            )
            val_lbl.pack(side=tk.RIGHT)


class HorizontalBarBreakdown(tk.Frame):
    """
    Gráfico de barras horizontales para desglosar la basura encontrada
    por cada categoría con proporciones visuales y colores temáticos.
    """
    CATEGORY_COLORS = {
        "user_temp": "#3B82F6",            # Azul
        "system_temp": "#6366F1",          # Índigo
        "recycle_bin": "#10B981",          # Verde esmeralda
        "browser_chrome": "#F59E0B",       # Ámbar / Amarillo
        "browser_edge": "#06B6D4",         # Cian
        "browser_brave": "#F97316",        # Naranja
        "browser_firefox": "#EC4899",      # Rosa / Magenta
        "browser_opera": "#EF4444",        # Rojo Opera
        "browser_vivaldi": "#F43F5E",      # Frambuesa Vivaldi
        "app_discord": "#5865F2",          # Blurple Discord
        "app_spotify": "#1DB954",          # Verde Spotify
        "app_vscode": "#007ACC",           # Azul VS Code
        "crash_dumps": "#DC2626",          # Rojo oscuro
        "thumbnail_cache": "#8B5CF6",      # Violeta
        "windows_update_cache": "#14B8A6", # Teal
        "windows_delivery_opt": "#0EA5E9", # Sky Blue
        "windows_logs": "#D97706",         # Ámbar oscuro
        "prefetch": "#A855F7"              # Púrpura
    }

    def __init__(self, parent, bg_color="#1B1E2B", **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color

        # Canvas con scroll vertical para cuando hay muchas categorías
        self.canvas = tk.Canvas(self, bg=self.bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.rows_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.rows_frame.bind("<MouseWheel>", _on_mousewheel)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.show_placeholder("Presiona 'Escanear Archivos Basura' para generar el gráfico.")

    def show_placeholder(self, text):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        lbl = tk.Label(
            self.rows_frame,
            text=text,
            font=("Segoe UI", 9, "italic"),
            bg=self.bg_color,
            fg="#6B7280",
            pady=30
        )
        lbl.pack(expand=True)

    def set_data(self, categories_data):
        """
        categories_data: lista de diccionarios:
        [{'key': 'user_temp', 'name': 'Temporales', 'size': 1024, 'size_str': '1.0 GB', 'count': 50}, ...]
        """
        for w in self.rows_frame.winfo_children():
            w.destroy()

        # Filtrar solo elementos con tamaño > 0 y ordenar descendente
        valid_items = [item for item in categories_data if item.get("size", 0) > 0]
        valid_items.sort(key=lambda x: x.get("size", 0), reverse=True)

        if not valid_items:
            self.show_placeholder("No se encontraron archivos basura. ¡Tu PC está totalmente limpia!")
            return

        total_size = sum(item["size"] for item in valid_items)
        max_size = max(item["size"] for item in valid_items)

        for item in valid_items:
            cat_key = item.get("key", "")
            cat_name = item.get("name", "")
            cat_size = item.get("size", 0)
            size_str = item.get("size_str", "0 B")
            color = self.CATEGORY_COLORS.get(cat_key, "#3B82F6")

            pct_total = (cat_size / total_size * 100.0) if total_size > 0 else 0.0
            bar_pct = (cat_size / max_size) if max_size > 0 else 0.0

            row = tk.Frame(self.rows_frame, bg=self.bg_color, pady=3)
            row.pack(fill=tk.X, padx=4)

            # Nombre de categoría
            lbl_name = tk.Label(
                row,
                text=cat_name,
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_color,
                fg="#E5E7EB",
                width=24,
                anchor="w"
            )
            lbl_name.pack(side=tk.LEFT)

            # Canvas con barra de progreso visual
            canvas_w = 230
            canvas_h = 14
            c = tk.Canvas(row, width=canvas_w, height=canvas_h, bg="#12141D", highlightthickness=0)
            c.pack(side=tk.LEFT, padx=8)

            # Fondo de la barra
            c.create_rectangle(0, 0, canvas_w, canvas_h, fill="#24283B", outline="")

            # Barra rellena
            fill_w = max(4, int(canvas_w * bar_pct))
            c.create_rectangle(0, 0, fill_w, canvas_h, fill=color, outline="")

            # Texto de tamaño y porcentaje a la derecha
            lbl_val = tk.Label(
                row,
                text=f"{size_str} ({pct_total:.1f}%)",
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_color,
                fg="#F9FAFB",
                width=16,
                anchor="e"
            )
            lbl_val.pack(side=tk.RIGHT)
