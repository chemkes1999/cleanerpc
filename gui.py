"""
PyClean Pro - Interfaz Gráfica de Usuario (GUI) con Gráficas Visuales
Interfaz moderna en modo oscuro desarrollada con Tkinter / TTK y gráficos interactivos.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
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
        self.root.title("PyClean Pro - Optimizador y Limpiador con Gráficas")
        self.root.geometry("1060x820")
        self.root.minsize(940, 720)
        self.root.configure(bg=DarkTheme.BG_DARK)

        self.is_admin = cleaner.is_admin()
        self.categories = cleaner.get_target_categories()
        self.cat_vars = {}
        self.cat_labels = {}
        self.cat_stats = {}
        self.is_running = False

        self._configure_styles()
        self._build_ui()
        self.refresh_system_charts()

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
            padding=[20, 8],
            font=("Segoe UI", 10, "bold"),
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

        # Barra de progreso
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=DarkTheme.BG_DARK,
            background=DarkTheme.ACCENT,
            thickness=8,
            borderwidth=0
        )

    def _build_ui(self):
        main_container = tk.Frame(self.root, bg=DarkTheme.BG_DARK)
        main_container.pack(fill=tk.BOTH, expand=True, padx=18, pady=14)

        # 1. Cabecera principal
        self._build_header(main_container)

        # 2. Barra de acciones rápidas
        self._build_action_bar(main_container)

        # 3. Pestañas (Notebook): Dashboard Gráfico y Centro de Limpieza
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

        # 4. Consola de Log y Barra de Progreso Inferior
        self._build_log_console(main_container)

    def _build_header(self, parent):
        header_frame = tk.Frame(parent, bg=DarkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Título y subtítulo
        title_box = tk.Frame(header_frame, bg=DarkTheme.BG_DARK)
        title_box.pack(side=tk.LEFT)

        title_label = tk.Label(
            title_box,
            text="⚡ PyClean Pro",
            font=("Segoe UI", 17, "bold"),
            bg=DarkTheme.BG_DARK,
            fg=DarkTheme.TEXT_MAIN
        )
        title_label.pack(anchor="w")

        sub_label = tk.Label(
            title_box,
            text="Optimizador y limpiador de archivos residuales con gráficas en tiempo real",
            font=("Segoe UI", 9),
            bg=DarkTheme.BG_DARK,
            fg=DarkTheme.TEXT_MUTED
        )
        sub_label.pack(anchor="w")

        # Estado de Permisos UAC
        badge_box = tk.Frame(header_frame, bg=DarkTheme.BG_DARK)
        badge_box.pack(side=tk.RIGHT, pady=2)

        if self.is_admin:
            tk.Label(
                badge_box,
                text="🛡️ MODO ADMINISTRADOR",
                font=("Segoe UI", 9, "bold"),
                bg="#064E3B",
                fg="#34D399",
                padx=10,
                pady=4
            ).pack(side=tk.RIGHT)
        else:
            tk.Button(
                badge_box,
                text="🚀 Reabrir como Admin",
                font=("Segoe UI", 9, "bold"),
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
                font=("Segoe UI", 9),
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
            padx=16,
            pady=7,
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
            padx=16,
            pady=7,
            command=self.action_clean
        )
        self.btn_clean.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_ram = tk.Button(
            action_bar,
            text="⚡ Liberar Memoria RAM",
            font=("Segoe UI", 9, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            activebackground="#4B5563",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=7,
            command=self.action_optimize_ram
        )
        self.btn_ram.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_dns = tk.Button(
            action_bar,
            text="🌐 Vaciar Caché DNS",
            font=("Segoe UI", 9, "bold"),
            bg="#374151",
            fg="#F3F4F6",
            activebackground="#4B5563",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=7,
            command=self.action_flush_dns
        )
        self.btn_dns.pack(side=tk.LEFT)

    def _build_charts_tab(self, parent):
        # Contenedor dividido en 2 columnas:
        # Columna Izquierda: 2 Gráficos Donut (Disco y RAM)
        # Columna Derecha: Gráfico de Barras de Distribución de Basura
        charts_layout = tk.Frame(parent, bg=DarkTheme.BG_DARK)
        charts_layout.pack(fill=tk.BOTH, expand=True, pady=6)

        # Panel Izquierdo: Donut Charts
        left_panel = tk.Frame(charts_layout, bg=DarkTheme.BG_DARK)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Donut 1: Disco C:
        card_disk_chart = tk.Frame(left_panel, bg=DarkTheme.BG_CARD, padx=14, pady=10)
        card_disk_chart.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            card_disk_chart,
            text="💾 Almacenamiento Disco (C:)",
            font=("Segoe UI", 10, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(anchor="w")

        self.donut_disk = DonutChart(card_disk_chart, size=150, bg_color=DarkTheme.BG_CARD)
        self.donut_disk.pack()

        # Donut 2: Memoria RAM
        card_ram_chart = tk.Frame(left_panel, bg=DarkTheme.BG_CARD, padx=14, pady=10)
        card_ram_chart.pack(fill=tk.X)

        tk.Label(
            card_ram_chart,
            text="🧠 Estado de Memoria RAM",
            font=("Segoe UI", 10, "bold"),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MAIN
        ).pack(anchor="w")

        self.donut_ram = DonutChart(card_ram_chart, size=150, bg_color=DarkTheme.BG_CARD)
        self.donut_ram.pack()

        # Panel Derecho: Gráfico de Distribución de Archivos Basura
        right_panel = tk.Frame(charts_layout, bg=DarkTheme.BG_CARD, padx=16, pady=12)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_right = tk.Frame(right_panel, bg=DarkTheme.BG_CARD)
        top_right.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            top_right,
            text="📊 Distribución de Archivos Basura por Categoría",
            font=("Segoe UI", 11, "bold"),
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
            text="Proporción de espacio ocupado por cada tipo de residuo en el sistema:",
            font=("Segoe UI", 8),
            bg=DarkTheme.BG_CARD,
            fg=DarkTheme.TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        # Canvas con scroll para el gráfico de barras
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
            text="Selecciona las carpetas y cachés que deseas incluir en la limpieza:",
            font=("Segoe UI", 10, "bold"),
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

        # Canvas con scroll para las categorías
        canvas_frame = tk.Frame(cat_card, bg=DarkTheme.BG_CARD)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=DarkTheme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DarkTheme.BG_CARD)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=980)
        canvas.configure(yscrollcommand=scrollbar.set)

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
                font=("Segoe UI", 9),
                bg=DarkTheme.BG_CARD,
                fg=DarkTheme.TEXT_MUTED
            )
            lbl_stat.pack(side=tk.RIGHT, padx=10)
            self.cat_labels[cat_key] = lbl_stat

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

        self.log("⚡ PyClean Pro iniciado. Haz clic en 'Escanear Archivos Basura' para analizar tu sistema.", "info")

    def log(self, message: str, tag: str = "dim"):
        self.txt_log.insert(tk.END, f"{message}\n", tag)
        self.txt_log.see(tk.END)

    def toggle_select_all(self):
        val = self.var_select_all.get()
        for var in self.cat_vars.values():
            var.set(val)

    def refresh_system_charts(self):
        """Actualiza los gráficos Donut de Disco C: y Memoria RAM."""
        stats = cleaner.get_system_stats()

        # 1. Gráfica Donut de Disco
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
            center_subtitle=f"{disk_free_gb:.0f} GB Libres"
        )

        # 2. Gráfica Donut de Memoria RAM
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
        self.is_running = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_scan.config(state=state)
        self.btn_clean.config(state=state)
        self.btn_ram.config(state=state)
        self.btn_dns.config(state=state)

        if busy:
            self.lbl_progress_status.config(text=status_text)
            self.main_progressbar.start(10)
        else:
            self.lbl_progress_status.config(text=status_text or "Listo")
            self.main_progressbar.stop()

    def request_elevation(self):
        if messagebox.askyesno(
            "Permisos de Administrador",
            "¿Deseas reiniciar la aplicación con privilegios de Administrador?\n\n"
            "Esto permitirá limpiar archivos temporales protegidos del sistema, "
            "la caché de Windows Update y registros Prefetch."
        ):
            cleaner.request_admin_elevation()

    # --- Acciones Asíncronas ---

    def action_scan(self):
        if self.is_running:
            return

        def _worker():
            self.set_ui_busy(True, "Escaneando archivos basura...")
            self.log("▶ Iniciando escaneo y análisis gráfico...", "info")

            total_size_all = 0
            total_files_all = 0
            breakdown_data = []

            for cat_key, cat_data in self.categories.items():
                if not self.cat_vars[cat_key].get():
                    continue

                self.lbl_progress_status.config(text=f"Analizando: {cat_data['name']}...")
                size, count, _ = cleaner.scan_category(cat_key, cat_data)
                self.cat_stats[cat_key] = {"size": size, "files": count}

                total_size_all += size
                total_files_all += count

                size_str = cleaner.format_size(size)
                self.cat_labels[cat_key].config(
                    text=f"{size_str} ({count:,} archivos)",
                    fg=DarkTheme.SUCCESS if size > 0 else DarkTheme.TEXT_MUTED
                )

                if size > 0:
                    breakdown_data.append({
                        "key": cat_key,
                        "name": cat_data["name"],
                        "size": size,
                        "size_str": size_str,
                        "count": count
                    })

            # Actualizar gráfico de barras
            self.bar_chart.set_data(breakdown_data)
            self.lbl_chart_total.config(text=f"Total: {cleaner.format_size(total_size_all)}")

            self.log(
                f"✔ Escaneo finalizado: {cleaner.format_size(total_size_all)} recuperables en {total_files_all:,} archivos.",
                "success"
            )

            self.refresh_system_charts()
            self.set_ui_busy(False, "Escaneo completado")

            # Llevar al usuario a la pestaña de gráficas si estaba en otra
            self.notebook.select(self.tab_charts)

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
            "Solo se eliminarán archivos temporales y cachés seguras. "
            "Los archivos protegidos o en uso se omitirán automáticamente."
        ):
            return

        def _worker():
            self.set_ui_busy(True, "Limpiando archivos seleccionados...")
            self.log("▶ Iniciando proceso de eliminación...", "info")

            total_freed = 0
            total_deleted = 0
            total_skipped = 0

            for cat_key in selected_keys:
                cat_data = self.categories[cat_key]
                self.lbl_progress_status.config(text=f"Limpiando: {cat_data['name']}...")

                freed, deleted, skipped = cleaner.clean_category(cat_key, cat_data)
                total_freed += freed
                total_deleted += deleted
                total_skipped += skipped

                freed_str = cleaner.format_size(freed)
                self.cat_labels[cat_key].config(
                    text=f"Liberado: {freed_str}",
                    fg=DarkTheme.TEXT_MUTED
                )
                self.log(f"  ✔ {cat_data['name']}: {freed_str} liberados ({deleted} eliminados, {skipped} en uso).", "dim")

            self.log(
                f"✨ Limpieza completada con éxito: Se liberaron {cleaner.format_size(total_freed)} ({total_deleted:,} archivos eliminados).",
                "success"
            )

            # Restablecer gráfico de barras a vacío/limpio
            self.bar_chart.show_placeholder("¡Tu PC está totalmente limpia y optimizada!")
            self.lbl_chart_total.config(text="Total: 0 B")

            self.refresh_system_charts()
            self.set_ui_busy(False, "Limpieza finalizada")

            messagebox.showinfo(
                "Limpieza Completada",
                f"¡Limpieza finalizada con éxito!\n\n"
                f"Espacio liberado: {cleaner.format_size(total_freed)}\n"
                f"Archivos eliminados: {total_deleted:,}\n"
                f"Archivos omitidos (en uso): {total_skipped:,}"
            )

        threading.Thread(target=_worker, daemon=True).start()

    def action_optimize_ram(self):
        if self.is_running:
            return

        def _worker():
            self.set_ui_busy(True, "Optimizando memoria RAM...")
            self.log("▶ Optimizando páginas de memoria RAM...", "info")
            procs = cleaner.optimize_ram()
            self.log(f"✔ Memoria optimizada: Se compactaron las páginas de {procs} procesos.", "success")
            self.refresh_system_charts()
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
                messagebox.showinfo("Caché DNS", "Caché de resolución DNS de Windows vaciada con éxito.")
            else:
                self.log(f"⚠️ Aviso al vaciar DNS: {msg}", "warning")
                messagebox.showwarning("Caché DNS", f"Aviso al vaciar DNS:\n{msg}")
            self.set_ui_busy(False, "Listo")

        threading.Thread(target=_worker, daemon=True).start()
