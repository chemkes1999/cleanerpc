"""
PyClean Pro - Interfaz Gráfica de Usuario (GUI) con Gráficas Visuales
Interfaz moderna en modo oscuro desarrollada con Tkinter / TTK, gráficos interactivos,
soporte multi-disco, visor de archivos pesados y gestor de programas de inicio.
"""

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cleaner
from charts import DonutChart, HorizontalBarBreakdown


class DarkTheme:
    BG_DARK = "#0F111A"
    BG_CARD = "#181B26"
    BG_CARD_HOVER = "#222636"
    BORDER = "#282C3F"
    ACCENT = "#3B82F6"
    ACCENT_HOVER = "#2563EB"
    SUCCESS = "#10B981"
    SUCCESS_HOVER = "#059669"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    TEXT_MAIN = "#F9FAFB"
    TEXT_MUTED = "#9CA3AF"
    TEXT_DIM = "#6B7280"
    LOG_BG = "#0B0C12"


class PyCleanGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyClean Pro v2.0 - Suite de Optimización y Limpieza")
        self.root.geometry("1080x840")
        self.root.minsize(960, 720)
        self.root.configure(bg=DarkTheme.BG_DARK)

        self.is_admin = cleaner.is_admin()
        self.config = cleaner.load_config()
        self.categories = cleaner.get_target_categories()
        self.drives = cleaner.get_system_drives()
        
        default_drive = self.drives[0]["letter"] if self.drives else "C:\\"
        self.selected_drive = tk.StringVar(value=default_drive)

        self.cat_vars = {}
        self.cat_labels = {}
        self.cat_stats = {}
        self.last_scanned_items = []
        self.is_running = False

        self._configure_styles()
        self._build_ui()
        self.refresh_system_charts()
        self.load_startup_list()

    def run_on_ui(self, fn, *args, **kwargs):
        """Despachador thread-safe para actualizar widgets Tkinter desde hilos secundarios."""
        try:
            self.root.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=DarkTheme.BG_DARK, foreground=DarkTheme.TEXT_MAIN)
        style.configure("TFrame", background=DarkTheme.BG_DARK)
        style.configure("Card.TFrame", background=DarkTheme.BG_CARD)

        # Pestañas personalizadas (Dark Notebook)
        style.configure("Dark.TNotebook", background=DarkTheme.BG_DARK, borderwidth=0)
        style.configure(
            "Dark.TNotebook.Tab",
            background=DarkTheme.BG_CARD,
            foreground=DarkTheme.TEXT_MUTED,
            padding=[16, 7],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", DarkTheme.ACCENT), ("active", DarkTheme.BG_CARD_HOVER)],
            foreground=[("selected", "#FFFFFF"), ("active", "#FFFFFF")]
        )

        # Checkbuttons
        style.configure(
            "Dark.TCheckbutton",
            background=DarkTheme.BG_CARD,
            foreground=DarkTheme.TEXT_MAIN,
            font=("Segoe UI", 9),
            indicatorbackground=DarkTheme.BG_DARK,
            indicatorforeground=DarkTheme.ACCENT
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", DarkTheme.BG_CARD)],
            foreground=[("active", DarkTheme.TEXT_MAIN)]
        )

        # Combobox
        style.configure(
            "Dark.TCombobox",
            fieldbackground=DarkTheme.BG_DARK,
            background=DarkTheme.BG_CARD,
            foreground=DarkTheme.TEXT_MAIN,
            arrowcolor=DarkTheme.TEXT_MAIN
        )

        # Barra de progreso
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=DarkTheme.BG_DARK,
            background=DarkTheme.ACCENT,
            thickness=8,
            borderwidth=0
        )

        # Treeview para programas de inicio
        style.configure(
            "Dark.Treeview",
            background=DarkTheme.BG_CARD,
            foreground=DarkTheme.TEXT_MAIN,
            fieldbackground=DarkTheme.BG_CARD,
            font=("Segoe UI", 9),
            rowheight=26,
            borderwidth=0
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=DarkTheme.BG_DARK,
            foreground=DarkTheme.TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
            borderwidth=1,
            relief=tk.FLAT
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", DarkTheme.ACCENT)],
            foreground=[("selected", "#FFFFFF")]
        )

    def _build_ui(self):
        main_container = tk.Frame(self.root, bg=DarkTheme.BG_DARK)
        main_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # 1. Cabecera principal
        self._build_header(main_container)

        # 2. Barra de acciones rápidas
        self._build_action_bar(main_container)

        # 3. Pestañas (Notebook): Dashboard, Limpieza, Inicio de Windows, Configuración
        self.notebook = ttk.Notebook(main_container, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Pestaña 1: Gráficas y Métricas
        self.tab_charts = tk.Frame(self.notebook, bg=DarkTheme.BG_DARK)
        self.notebook.add(self.tab_charts, text="  📊 Gráficas y Dashboard  ")
        self._build_charts_tab(self.tab_charts)

        # Pestaña 2: Limpieza y Categorías
        self.tab_cleanup = tk.Frame(self.notebook, bg=DarkTheme.BG_DARK)
        self.notebook.add(self.tab_cleanup, text="  🧹 Opciones de Limpieza  ")
        self._build_cleanup_tab(self.tab_cleanup)

        # Pestaña 3: Programas de Inicio
        self.tab_startup = tk.Frame(self.notebook, bg=DarkTheme.BG_DARK)
        self.notebook.add(self.tab_startup, text="  🚀 Inicio de Windows  ")
        self._build_startup_tab(self.tab_startup)

        # Pestaña 4: Configuración y Exclusiones
        self.tab_settings = tk.Frame(self.notebook, bg=DarkTheme.BG_DARK)
        self.notebook.add(self.tab_settings, text="  ⚙️ Configuración y Exclusiones  ")
        self._build_settings_tab(self.tab_settings)

        # 4. Consola de Log y Barra de Progreso Inferior
        self._build_log_console(main_container)

    def _build_header(self, parent):
        header_frame = tk.Frame(parent, bg=DarkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_box = tk.Frame(header_frame, bg=DarkTheme.BG_DARK)
        title_box.pack(side=tk.LEFT)

        title_label = tk.Label(
            title_box,
            text="⚡ PyClean Pro v2.0",
            font=("Segoe UI", 16, "bold"),
            bg=DarkTheme.BG_DARK,
            fg=DarkTheme.TEXT_MAIN
        )
        title_label.pack(anchor="w")

        sub_label = tk.Label(
            title_box,
            text="Suite de optimización, limpieza segura y aceleración para Windows",
            font=("Segoe UI", 8),
            bg=DarkTheme.BG_DARK,
            fg=DarkTheme.TEXT_MUTED
        )
        sub_label.pack(anchor="w")

        # Estado UAC
        badge_box = tk.Frame(header_frame, bg=DarkTheme.BG_DARK)
        badge_box.pack(side=tk.RIGHT, pady=2)

        if self.is_admin:
            tk.Label(
                badge_box,
                text="🛡️ MODO ADMINISTRADOR",
                font=("Segoe UI", 8, "bold"),
                bg="#064E3B",
                fg="#34D399",
                padx=10,
                pady=4
            ).pack(side=tk.RIGHT)
        else:
            tk.Button(
                badge_box,
                text="🚀 Reabrir como Admin",
                font=("Segoe UI", 8, "bold"),
                bg="#78350F",
                fg="#FCD34D",
                activebackground="#92400E",
                activeforeground="#FDE68A",
                relief=tk.FLAT,
                cursor="hand2",
                command=self.request_elevation,
                padx=10,
                pady=4
            ).pack(side=tk.RIGHT)

            tk.Label(
                badge_box,
                text="⚠️ Modo Estándar",
                font=("Segoe UI", 8),
                bg=DarkTheme.BG_DARK,
                fg=DarkTheme.TEXT_MUTED,
                padx=6
            ).pack(side=tk.RIGHT)

    def _build_action_bar(self, parent):
        action_bar = tk.Frame(parent, bg=DarkTheme.BG_DARK)
        action_bar.pack(fill=tk.X, pady=(0, 10))

        self.btn_scan = tk.Button(
            action_bar,
            text="🔍 Escanear Archivos Basura",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self.action_scan
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clean = tk.Button(
            action_bar,
            text="🧹 Limpiar Basura",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            activebackground="#047857",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self.action_clean
        )
        self.btn_clean.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_inspect = tk.Button(
            action_bar,
            text="📂 Inspeccionar Basura",
            font=("Segoe UI", 9, "bold"),
            bg="#4B5563",
            fg="#F3F4F6",
            activebackground="#374151",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.action_inspect_files,
            state=tk.DISABLED
        )
        self.btn_inspect.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_ram = tk.Button(
            action_bar,
            text="⚡ Liberar RAM",
            font=("Segoe UI", 9, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            activebackground="#4B5563",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.action_optimize_ram
        )
        self.btn_ram.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_dns = tk.Button(
            action_bar,
            text="🌐 Vaciar DNS",
            font=("Segoe UI", 9, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            activebackground="#4B5563",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.action_flush_dns
        )
        self.btn_dns.pack(side=tk.LEFT)

    def _build_charts_tab(self, parent):
        charts_layout = tk.Frame(parent, bg=DarkTheme.BG_DARK)
        charts_layout.pack(fill=tk.BOTH, expand=True, pady=6)

        # Panel Izquierdo: Donut Charts
        left_panel = tk.Frame(charts_layout, bg=DarkTheme.BG_DARK)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Donut 1: Disco con selector dinámico
        card_disk = tk.Frame(left_panel, bg=DarkTheme.BG_CARD, padx=12, pady=8)
        card_disk.pack(fill=tk.X, pady=(0, 8))

        disk_header = tk.Frame(card_disk, bg=DarkTheme.BG_CARD)
        disk_header.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            disk_header,
            text="💾 Almacenamiento",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT)

        drive_letters = [d["letter"] for d in self.drives] if self.drives else ["C:\\"]
        self.combo_drive = ttk.Combobox(
            disk_header,
            textvariable=self.selected_drive,
            values=drive_letters,
            state="readonly",
            width=5,
            style="Dark.TCombobox"
        )
        self.combo_drive.pack(side=tk.RIGHT)
        self.combo_drive.bind("<<ComboboxSelected>>", lambda e: self.refresh_system_charts())

        self.donut_disk = DonutChart(card_disk, size=140, bg_color=DarkTheme.BG_CARD)
        self.donut_disk.pack()

        # Donut 2: RAM
        card_ram = tk.Frame(left_panel, bg=DarkTheme.BG_CARD, padx=12, pady=8)
        card_ram.pack(fill=tk.X)

        tk.Label(
            card_ram,
            text="🧠 Memoria RAM",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(anchor="w")

        self.donut_ram = DonutChart(card_ram, size=140, bg_color=DarkTheme.BG_CARD)
        self.donut_ram.pack()

        # Panel Derecho: Distribución de Basura
        right_panel = tk.Frame(charts_layout, bg=DarkTheme.BG_CARD, padx=14, pady=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_right = tk.Frame(right_panel, bg=DarkTheme.BG_CARD)
        top_right.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            top_right,
            text="📊 Distribución de Archivos Basura por Categoría",
            font=("Segoe UI", 10, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT)

        self.lbl_chart_total = tk.Label(
            top_right,
            text="Total: 0 B",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.SUCCESS
        )
        self.lbl_chart_total.pack(side=tk.RIGHT)

        tk.Label(
            right_panel,
            text="Proporción de espacio recuperable desglosado por aplicación y componentes de Windows:",
            font=("Segoe UI", 8),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MUTED
        ).pack(anchor="w", pady=(0, 6))

        bar_container = tk.Frame(right_panel, bg=DarkTheme.BG_CARD)
        bar_container.pack(fill=tk.BOTH, expand=True)

        self.bar_chart = HorizontalBarBreakdown(bar_container, bg_color=DarkTheme.BG_CARD)
        self.bar_chart.pack(fill=tk.BOTH, expand=True)

    def _build_cleanup_tab(self, parent):
        cat_card = tk.Frame(parent, bg=DarkTheme.BG_CARD, padx=14, pady=10)
        cat_card.pack(fill=tk.BOTH, expand=True, pady=6)

        top_bar = tk.Frame(cat_card, bg=DarkTheme.BG_CARD)
        top_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            top_bar,
            text="Selecciona las categorías que deseas incluir en el escaneo y limpieza:",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT)

        self.var_select_all = tk.BooleanVar(value=True)
        chk_all = ttk.Checkbutton(
            top_bar,
            text="Seleccionar Todo",
            variable=self.var_select_all,
            style="Dark.TCheckbutton",
            command=self.toggle_select_all
        )
        chk_all.pack(side=tk.RIGHT)

        canvas_frame = tk.Frame(cat_card, bg=DarkTheme.BG_CARD)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=DarkTheme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DarkTheme.BG_CARD)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(canvas_window, width=e.width)
        )

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for cat_key, cat_data in self.categories.items():
            row_frame = tk.Frame(scrollable_frame, bg=DarkTheme.BG_CARD, pady=4)
            row_frame.pack(fill=tk.X, expand=True, padx=4)

            var = tk.BooleanVar(value=True)
            self.cat_vars[cat_key] = var

            chk = ttk.Checkbutton(
                row_frame,
                text=cat_data["name"],
                variable=var,
                style="Dark.TCheckbutton"
            )
            chk.pack(side=tk.LEFT)

            if cat_data["requires_admin"] and not self.is_admin:
                tk.Label(
                    row_frame,
                    text="[Requiere Admin]",
                    font=("Segoe UI", 7, "bold"),
                    bg=DarkTheme.BG_CARD,
                    fg=DarkTheme.WARNING
                ).pack(side=tk.LEFT, padx=6)

            tk.Label(
                row_frame,
                text=f"- {cat_data['desc']}",
                font=("Segoe UI", 8),
                bg=DarkTheme.BG_CARD,
                fg=DarkTheme.TEXT_DIM
            ).pack(side=tk.LEFT, padx=6)

            lbl_stat = tk.Label(
                row_frame,
                text="Sin analizar",
                font=("Segoe UI", 8),
                bg=DarkTheme.BG_CARD,
                fg=DarkTheme.TEXT_MUTED
            )
            lbl_stat.pack(side=tk.RIGHT, padx=10)
            self.cat_labels[cat_key] = lbl_stat

    def _build_startup_tab(self, parent):
        """Pestaña para gestionar programas de inicio en el Registro de Windows."""
        card = tk.Frame(parent, bg=DarkTheme.BG_CARD, padx=14, pady=10)
        card.pack(fill=tk.BOTH, expand=True, pady=6)

        top_box = tk.Frame(card, bg=DarkTheme.BG_CARD)
        top_box.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_box,
            text="Programas de Inicio Automático con Windows:",
            font=("Segoe UI", 10, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT)

        btn_refresh_startup = tk.Button(
            top_box,
            text="🔄 Actualizar",
            font=("Segoe UI", 8, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.load_startup_list
        )
        btn_refresh_startup.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_toggle_startup = tk.Button(
            top_box,
            text="⚡ Habilitar / Deshabilitar",
            font=("Segoe UI", 8, "bold"),
            bg=DarkTheme.ACCENT,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=3,
            command=self.toggle_selected_startup
        )
        self.btn_toggle_startup.pack(side=tk.RIGHT)

        # Treeview de programas
        cols = ("name", "status", "scope", "command")
        self.tree_startup = ttk.Treeview(
            card,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse"
        )
        self.tree_startup.heading("name", text="Nombre del Programa")
        self.tree_startup.heading("status", text="Estado")
        self.tree_startup.heading("scope", text="Ámbito")
        self.tree_startup.heading("command", text="Comando / Ruta")

        self.tree_startup.column("name", width=200, anchor="w")
        self.tree_startup.column("status", width=110, anchor="center")
        self.tree_startup.column("scope", width=140, anchor="w")
        self.tree_startup.column("command", width=460, anchor="w")

        scroll_y = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.tree_startup.yview)
        self.tree_startup.configure(yscrollcommand=scroll_y.set)

        self.tree_startup.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_settings_tab(self, parent):
        """Pestaña de configuración de seguridad (filtro de edad) y lista blanca de exclusiones."""
        card = tk.Frame(parent, bg=DarkTheme.BG_CARD, padx=16, pady=12)
        card.pack(fill=tk.BOTH, expand=True, pady=6)

        # Sección 1: Regla de Retención de Temporales
        sec1 = tk.LabelFrame(
            card,
            text=" 🛡️ Seguridad de Eliminación (Filtro de Antigüedad) ",
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=10
        )
        sec1.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            sec1,
            text="Ignorar archivos temporales modificados hace menos de:",
            font=("Segoe UI", 9),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.var_min_age = tk.IntVar(value=self.config.get("min_age_hours", 24))
        spin_age = ttk.Spinbox(sec1, from_=0, to=168, textvariable=self.var_min_age, width=5)
        spin_age.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(
            sec1,
            text="horas  (Recomendado: 24h para evitar corromper instaladores en ejecución). Usa 0 para borrar todo.",
            font=("Segoe UI", 8),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MUTED
        ).pack(side=tk.LEFT)

        # Sección 2: Lista Blanca de Exclusiones
        sec2 = tk.LabelFrame(
            card,
            text=" 🚫 Lista Blanca de Exclusiones (Carpetas que NUNCA se tocarán) ",
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=10
        )
        sec2.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_row = tk.Frame(sec2, bg=DarkTheme.BG_CARD)
        btn_row.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            btn_row,
            text="➕ Añadir Carpeta",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.add_exclusion
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_row,
            text="🗑️ Eliminar Seleccionado",
            font=("Segoe UI", 8, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.remove_exclusion
        ).pack(side=tk.LEFT)

        # Listbox de exclusiones
        list_frame = tk.Frame(sec2, bg=DarkTheme.BG_CARD)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.list_exclusions = tk.Listbox(
            list_frame,
            bg=DarkTheme.LOG_BG,
            fg=DarkTheme.TEXT_MAIN,
            selectbackground=DarkTheme.ACCENT,
            font=("Consolas", 9),
            relief=tk.FLAT,
            borderwidth=0
        )
        scroll_excl = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.list_exclusions.yview)
        self.list_exclusions.configure(yscrollcommand=scroll_excl.set)

        self.list_exclusions.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_excl.pack(side=tk.RIGHT, fill=tk.Y)

        for item in self.config.get("exclusions", []):
            self.list_exclusions.insert(tk.END, item)

        # Botón Guardar Cambios
        tk.Button(
            card,
            text="💾 Guardar Cambios de Configuración",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.SUCCESS,
            fg="#FFFFFF",
            activebackground=DarkTheme.SUCCESS_HOVER,
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=6,
            command=self.save_settings
        ).pack(anchor="e")

    def _build_log_console(self, parent):
        log_frame = tk.Frame(parent, bg=DarkTheme.BG_CARD, padx=12, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=False)

        prog_box = tk.Frame(log_frame, bg=DarkTheme.BG_CARD)
        prog_box.pack(fill=tk.X, pady=(0, 4))

        self.lbl_progress_status = tk.Label(
            prog_box, text="Listo", font=("Segoe UI", 8),
            bg=DarkTheme.BG_CARD, fg=DarkTheme.TEXT_MUTED
        )
        self.lbl_progress_status.pack(side=tk.LEFT)

        self.main_progressbar = ttk.Progressbar(
            prog_box, style="Custom.Horizontal.TProgressbar", mode="indeterminate"
        )
        self.main_progressbar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(12, 0))

        self.txt_log = tk.Text(
            log_frame,
            height=5,
            bg=DarkTheme.LOG_BG,
            fg=DarkTheme.TEXT_MUTED,
            insertbackground=DarkTheme.TEXT_MAIN,
            font=("Consolas", 8),
            relief=tk.FLAT,
            padx=8,
            pady=4,
            wrap=tk.WORD
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        self.txt_log.tag_configure("info", foreground="#60A5FA")
        self.txt_log.tag_configure("success", foreground="#34D399")
        self.txt_log.tag_configure("warning", foreground="#FBBF24")
        self.txt_log.tag_configure("danger", foreground="#F87171")
        self.txt_log.tag_configure("dim", foreground="#6B7280")

        self.log("⚡ PyClean Pro v2.0 iniciado. Haz clic en 'Escanear Archivos Basura' para comenzar.", "info")

    def log(self, message: str, tag: str = "dim"):
        def _do():
            self.txt_log.insert(tk.END, f"{message}\n", tag)
            self.txt_log.see(tk.END)
        self.run_on_ui(_do)

    def toggle_select_all(self):
        val = self.var_select_all.get()
        for var in self.cat_vars.values():
            var.set(val)

    def refresh_system_charts(self):
        """Actualiza los gráficos Donut de Disco y RAM con soporte para el disco seleccionado."""
        target_drive = self.selected_drive.get() or "C:\\"
        stats = cleaner.get_system_stats(drive=target_drive)

        disk_used_gb = stats["disk_used"] / (1024 ** 3)
        disk_free_gb = stats["disk_free"] / (1024 ** 3)
        disk_color = DarkTheme.DANGER if stats["disk_percent"] > 90 else (
            DarkTheme.WARNING if stats["disk_percent"] > 80 else DarkTheme.ACCENT
        )

        disk_segments = [
            {"value": stats["disk_used"], "color": disk_color, "label": "Usado", "text_val": f"{disk_used_gb:.1f} GB"},
            {"value": stats["disk_free"], "color": DarkTheme.SUCCESS, "label": "Libre", "text_val": f"{disk_free_gb:.1f} GB"}
        ]
        self.donut_disk.set_data(
            disk_segments,
            center_title=f"{stats['disk_percent']}%",
            center_subtitle=f"{disk_free_gb:.0f} GB Libres ({target_drive[:2]})"
        )

        ram_used_gb = stats["ram_used"] / (1024 ** 3)
        ram_avail_gb = stats["ram_avail"] / (1024 ** 3)
        ram_color = DarkTheme.DANGER if stats["ram_load"] > 85 else DarkTheme.ACCENT

        ram_segments = [
            {"value": stats["ram_used"], "color": ram_color, "label": "En uso", "text_val": f"{ram_used_gb:.1f} GB"},
            {"value": stats["ram_avail"], "color": "#24283B", "label": "Disponible", "text_val": f"{ram_avail_gb:.1f} GB"}
        ]
        self.donut_ram.set_data(
            ram_segments,
            center_title=f"{stats['ram_load']}%",
            center_subtitle=f"{ram_used_gb:.1f} GB Usados"
        )

    def set_ui_busy(self, busy: bool, status_text: str = ""):
        def _do():
            self.is_running = busy
            state = tk.DISABLED if busy else tk.NORMAL
            self.btn_scan.config(state=state)
            self.btn_clean.config(state=state)
            self.btn_ram.config(state=state)
            self.btn_dns.config(state=state)

            if len(self.last_scanned_items) > 0 and not busy:
                self.btn_inspect.config(state=tk.NORMAL)
            else:
                self.btn_inspect.config(state=tk.DISABLED)

            if busy:
                self.lbl_progress_status.config(text=status_text)
                self.main_progressbar.start(10)
            else:
                self.lbl_progress_status.config(text=status_text or "Listo")
                self.main_progressbar.stop()
        self.run_on_ui(_do)

    def request_elevation(self):
        if messagebox.askyesno(
            "Permisos de Administrador",
            "¿Deseas reiniciar la aplicación con privilegios de Administrador?\n\n"
            "Esto permitirá limpiar archivos protegidos del sistema, registros de Windows Update y registros Prefetch."
        ):
            cleaner.request_admin_elevation()

    # --- Gestión de Configuración y Exclusiones ---

    def add_exclusion(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta a excluir de la limpieza")
        if folder:
            norm_folder = os.path.abspath(folder)
            current_items = self.list_exclusions.get(0, tk.END)
            if norm_folder not in current_items:
                self.list_exclusions.insert(tk.END, norm_folder)

    def remove_exclusion(self):
        sel = self.list_exclusions.curselection()
        if sel:
            self.list_exclusions.delete(sel[0])

    def save_settings(self):
        try:
            min_age = int(self.var_min_age.get())
        except ValueError:
            min_age = 24
        exclusions = list(self.list_exclusions.get(0, tk.END))
        self.config["min_age_hours"] = min_age
        self.config["exclusions"] = exclusions
        if cleaner.save_config(self.config):
            messagebox.showinfo("Configuración", "Configuración guardada con éxito.")
            self.log(f"✔ Configuración actualizada: Antigüedad mínima {min_age}h, {len(exclusions)} exclusiones.", "info")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    # --- Gestión de Programas de Inicio ---

    def load_startup_list(self):
        for item in self.tree_startup.get_children():
            self.tree_startup.delete(item)
        self.startup_items = cleaner.get_startup_programs()
        for idx, prog in enumerate(self.startup_items):
            status_text = "✔ Habilitado" if prog["enabled"] else "❌ Deshabilitado"
            self.tree_startup.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(prog["name"], status_text, prog["scope"], prog["command"])
            )

    def toggle_selected_startup(self):
        sel = self.tree_startup.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecciona un programa de la lista para cambiar su estado.")
            return
        idx = int(sel[0])
        prog = self.startup_items[idx]
        success, msg = cleaner.toggle_startup_program(prog)
        if success:
            self.log(f"✔ Inicio: {msg}", "success")
            self.load_startup_list()
        else:
            messagebox.showwarning("Aviso", msg)

    # --- Acciones Asíncronas ---

    def action_scan(self):
        if self.is_running:
            return

        def _worker():
            self.set_ui_busy(True, "Escaneando archivos basura...")
            self.log("▶ Iniciando escaneo y análisis gráfico...", "info")

            min_age = self.config.get("min_age_hours", 24)
            exclusions = self.config.get("exclusions", [])

            total_size_all = 0
            total_files_all = 0
            breakdown_data = []
            all_items = []

            for cat_key, cat_data in self.categories.items():
                if not self.cat_vars[cat_key].get():
                    continue

                self.run_on_ui(lambda c=cat_data["name"]: self.lbl_progress_status.config(text=f"Analizando: {c}..."))
                size, count, items = cleaner.scan_category(cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions)
                self.cat_stats[cat_key] = {"size": size, "files": count}

                total_size_all += size
                total_files_all += count
                all_items.extend(items)

                size_str = cleaner.format_size(size)
                self.run_on_ui(
                    lambda k=cat_key, s=size_str, c=count, sz=size: self.cat_labels[k].config(
                        text=f"{s} ({c:,} archivos)",
                        fg=DarkTheme.SUCCESS if sz > 0 else DarkTheme.TEXT_MUTED
                    )
                )

                if size > 0:
                    breakdown_data.append({
                        "key": cat_key,
                        "name": cat_data["name"],
                        "size": size,
                        "size_str": size_str,
                        "count": count
                    })

            self.last_scanned_items = all_items

            def _finalize_ui():
                self.bar_chart.set_data(breakdown_data)
                self.lbl_chart_total.config(text=f"Total: {cleaner.format_size(total_size_all)}")
                self.refresh_system_charts()
                self.set_ui_busy(False, "Escaneo completado")
                self.notebook.select(self.tab_charts)

            self.run_on_ui(_finalize_ui)
            self.log(
                f"✔ Escaneo finalizado: {cleaner.format_size(total_size_all)} recuperables en {total_files_all:,} archivos.",
                "success"
            )

        threading.Thread(target=_worker, daemon=True).start()

    def action_clean(self):
        if self.is_running:
            return

        selected_keys = [k for k, v in self.cat_vars.items() if v.get()]
        if not selected_keys:
            messagebox.showinfo("Aviso", "No has seleccionado ninguna categoría para limpiar.")
            return

        if not messagebox.askyesno(
            "Confirmar Limpieza",
            "¿Estás seguro de que deseas eliminar los archivos basura seleccionados?\n\n"
            "Se respetará el filtro de antigüedad para proteger instalaciones recientes. "
            "Los archivos bloqueados por el sistema se omitirán automáticamente."
        ):
            return

        def _worker():
            self.set_ui_busy(True, "Limpiando archivos seleccionados...")
            self.log("▶ Iniciando proceso de eliminación...", "info")

            min_age = self.config.get("min_age_hours", 24)
            exclusions = self.config.get("exclusions", [])

            total_freed = 0
            total_deleted = 0
            total_skipped = 0

            for cat_key in selected_keys:
                cat_data = self.categories[cat_key]
                self.run_on_ui(lambda c=cat_data["name"]: self.lbl_progress_status.config(text=f"Limpiando: {c}..."))

                freed, deleted, skipped = cleaner.clean_category(
                    cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions
                )
                total_freed += freed
                total_deleted += deleted
                total_skipped += skipped

                freed_str = cleaner.format_size(freed)
                self.run_on_ui(
                    lambda k=cat_key, f=freed_str: self.cat_labels[k].config(
                        text=f"Liberado: {f}",
                        fg=DarkTheme.TEXT_MUTED
                    )
                )
                self.log(f"  ✔ {cat_data['name']}: {freed_str} liberados ({deleted} eliminados, {skipped} en uso).", "dim")

            self.last_scanned_items = []

            def _finalize_ui():
                self.bar_chart.show_placeholder("¡Tu PC está totalmente limpia y optimizada!")
                self.lbl_chart_total.config(text="Total: 0 B")
                self.refresh_system_charts()
                self.set_ui_busy(False, "Limpieza finalizada")
                messagebox.showinfo(
                    "Limpieza Completada",
                    f"¡Limpieza finalizada con éxito!\n\n"
                    f"Espacio liberado: {cleaner.format_size(total_freed)}\n"
                    f"Archivos eliminados: {total_deleted:,}\n"
                    f"Archivos omitidos (en uso o protegidos): {total_skipped:,}"
                )

            self.run_on_ui(_finalize_ui)
            self.log(
                f"✨ Limpieza completada con éxito: Se liberaron {cleaner.format_size(total_freed)} ({total_deleted:,} archivos eliminados).",
                "success"
            )

        threading.Thread(target=_worker, daemon=True).start()

    def action_inspect_files(self):
        """Abre un modal detallado con los archivos más pesados encontrados en el escaneo."""
        if not self.last_scanned_items:
            messagebox.showinfo("Inspeccionar", "Primero ejecuta un escaneo para ver los archivos encontrados.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Archivos Grandes Detectados en el Escaneo (Top 100)")
        dialog.geometry("860x520")
        dialog.configure(bg=DarkTheme.BG_DARK)
        dialog.transient(self.root)

        header = tk.Frame(dialog, bg=DarkTheme.BG_DARK, padx=14, pady=10)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"Archivos más pesados encontrados ({min(100, len(self.last_scanned_items))} de {len(self.last_scanned_items):,}):",
            font=("Segoe UI", 10, "bold"),
            bg=DarkTheme.BG_DARK,
            fg=DarkTheme.TEXT_MAIN
        ).pack(side=tk.LEFT)

        # Ordenar por tamaño descendente
        sorted_items = sorted(self.last_scanned_items, key=lambda x: x.get("size", 0), reverse=True)[:100]

        tree_frame = tk.Frame(dialog, bg=DarkTheme.BG_CARD, padx=10, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

        cols = ("size", "path")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Dark.Treeview")
        tree.heading("size", text="Tamaño")
        tree.heading("path", text="Ruta de Archivo")
        tree.column("size", width=120, anchor="e")
        tree.column("path", width=680, anchor="w")

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        for item in sorted_items:
            tree.insert("", tk.END, values=(cleaner.format_size(item["size"]), item["path"]))

        def _open_selected_folder():
            sel = tree.selection()
            if sel:
                val = tree.item(sel[0])["values"]
                path = val[1]
                if os.path.exists(path):
                    subprocess.Popen(["explorer.exe", f"/select,{path}"])

        btn_box = tk.Frame(dialog, bg=DarkTheme.BG_DARK, padx=14, pady=10)
        btn_box.pack(fill=tk.X)

        tk.Button(
            btn_box,
            text="📂 Abrir en Explorador de Windows",
            font=("Segoe UI", 9, "bold"),
            bg=DarkTheme.ACCENT,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=5,
            command=_open_selected_folder
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_box,
            text="Cerrar",
            font=("Segoe UI", 9),
            bg="#374151",
            fg="#F3F4F6",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=5,
            command=dialog.destroy
        ).pack(side=tk.RIGHT)

    def action_optimize_ram(self):
        if self.is_running:
            return

        def _worker():
            self.set_ui_busy(True, "Optimizando memoria RAM...")
            self.log("▶ Optimizando páginas de memoria RAM...", "info")
            procs = cleaner.optimize_ram()
            self.log(f"✔ Memoria optimizada: Se compactaron las páginas de {procs} procesos.", "success")
            self.run_on_ui(self.refresh_system_charts)
            self.set_ui_busy(False, "RAM Optimizada")

        threading.Thread(target=_worker, daemon=True).start()

    def action_flush_dns(self):
        if self.is_running:
            return

        def _worker():
            self.set_ui_busy(True, "Vaciando caché DNS...")
            self.log("▶ Ejecutando vaciado de caché DNS...", "info")
            success, msg = cleaner.flush_dns()
            if success:
                self.log("✔ Caché de resolución DNS vaciada correctamente.", "success")
                self.run_on_ui(lambda: messagebox.showinfo("Caché DNS", "Caché de resolución DNS de Windows vaciada con éxito."))
            else:
                self.log(f"⚠️ Aviso al vaciar DNS: {msg}", "warning")
                self.run_on_ui(lambda: messagebox.showwarning("Caché DNS", f"Aviso al vaciar DNS:\n{msg}"))
            self.set_ui_busy(False, "Listo")

        threading.Thread(target=_worker, daemon=True).start()
