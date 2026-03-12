#!/usr/bin/env python3
"""
HuggingFace Model Explorer GUI
Beautiful GUI application for browsing and ranking GGUF models
"""

import math
import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timezone
from enum import Enum
from tkinter import ttk, messagebox
from tkinter.font import Font
from typing import List, Optional
import pyperclip
import logging
from pathlib import Path
import json
import queue

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Создаём кастомный форматтер, который выводит extra-поля как JSON
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, "extra"):
            # Добавляем все поля из extra в основной словарь лога
            log_entry = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "event": record.getMessage(),
                **record.extra,
            }
            return json.dumps(log_entry, ensure_ascii=False)
        else:
            return super().format(record)

# Настраиваем логгер
handler = logging.FileHandler(LOG_DIR / "model_explorer.log", encoding="utf-8")
handler.setFormatter(StructuredFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    force=True,  # Перезаписывает настройки, если уже был логгер
)

try:
    from hf_best_models import (
        GGUFModelRanker,
        RankingMode,
        ModelInfo,
        CacheManager,
    )
except ImportError:
    messagebox.showerror(
        "Import Error",
        "Could not import from hf_best_models.py\n"
        "Make sure the file exists in the same directory.",
    )
    raise


class SortMode(Enum):
    TRENDING = "trending"
    LIKES = "likes"
    DOWNLOADS = "downloads"
    MODIFIED = "modified"
    SMART = "smart"


class AppStyle:
    """Application styling configuration - Light Theme"""

    BG_PRIMARY = "#f5f5f5"
    BG_SECONDARY = "#ffffff"
    BG_TERTIARY = "#e8e8e8"
    FG_PRIMARY = "#333333"
    FG_SECONDARY = "#666666"
    ACCENT = "#1a73e8"
    ACCENT_HOVER = "#1557b0"
    SUCCESS = "#1e7e34"
    WARNING = "#e65100"
    ERROR = "#c5221f"
    BORDER = "#dddddd"

    @classmethod
    def configure_styles(cls, style: ttk.Style):
        """Configure ttk styles for light theme"""
        style.theme_use("clam")

        style.configure(
            "Primary.TFrame",
            background=cls.BG_PRIMARY,
        )

        style.configure(
            "Secondary.TFrame",
            background=cls.BG_SECONDARY,
        )

        style.configure(
            "TFrame",
            background=cls.BG_PRIMARY,
        )

        style.configure(
            "TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.FG_PRIMARY,
            font=("Segoe UI", 10),
        )

        style.configure(
            "Title.TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.ACCENT,
            font=("Segoe UI", 14, "bold"),
        )

        style.configure(
            "Subtitle.TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.FG_SECONDARY,
            font=("Segoe UI", 9),
        )

        style.configure(
            "TButton",
            background=cls.BG_TERTIARY,
            foreground=cls.FG_PRIMARY,
            borderwidth=1,
            font=("Segoe UI", 9),
            padding=5,
        )

        style.map(
            "TButton",
            background=[
                ("active", cls.ACCENT_HOVER),
                ("pressed", cls.ACCENT),
            ],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Accent.TButton",
            background=cls.ACCENT,
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )

        style.map(
            "Accent.TButton",
            background=[
                ("active", cls.ACCENT_HOVER),
            ],
        )

        style.configure(
            "TRadiobutton",
            background=cls.BG_PRIMARY,
            foreground=cls.FG_PRIMARY,
            font=("Segoe UI", 10),
        )

        style.map(
            "TRadiobutton",
            indicatorcolor=[("selected", cls.ACCENT)],
            foreground=[("selected", cls.ACCENT)],
        )

        style.configure(
            "Treeview",
            background=cls.BG_SECONDARY,
            foreground=cls.FG_PRIMARY,
            fieldbackground=cls.BG_SECONDARY,
            font=("Consolas", 10),
            rowheight=28,
        )

        style.configure(
            "Treeview.Heading",
            background=cls.BG_TERTIARY,
            foreground=cls.FG_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )

        style.map(
            "Treeview.Heading",
            background=[
                ("active", cls.ACCENT),
            ],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=cls.BG_TERTIARY,
            troughcolor=cls.BG_SECONDARY,
            borderwidth=0,
            arrowcolor=cls.FG_PRIMARY,
        )

        style.configure(
            "TScale",
            background=cls.BG_PRIMARY,
            troughcolor=cls.BG_TERTIARY,
        )

        style.configure(
            "Status.TLabel",
            background=cls.BG_SECONDARY,
            foreground=cls.FG_SECONDARY,
            font=("Segoe UI", 9),
            padding=5,
        )


class CustomRangeSlider:
    """Custom range input widget with input fields"""

    def __init__(self, parent, min_val: int = 12, max_val: int = 64,
                 on_change_callback=None, **kwargs):
        self.parent = parent
        self.on_change_callback = on_change_callback  # Callback when values change

        self.frame = ttk.Frame(parent)

        ttk.Label(
            self.frame,
            text="Min:",
            style="TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.entry_min = ttk.Entry(
            self.frame,
            width=6,
            font=("Consolas", 10),
        )
        self.entry_min.pack(side=tk.LEFT, padx=(2, 5))
        self.entry_min.insert(0, str(min_val))

        ttk.Label(
            self.frame,
            text="B",
            style="TLabel",
        ).pack(side=tk.LEFT)

        ttk.Label(
            self.frame,
            text="-",
            style="TLabel",
            font=("Segoe UI", 12),
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            self.frame,
            text="Max:",
            style="TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)

        self.entry_max = ttk.Entry(
            self.frame,
            width=6,
            font=("Consolas", 10),
        )
        self.entry_max.pack(side=tk.LEFT, padx=(2, 5))
        self.entry_max.insert(0, str(max_val))

        ttk.Label(
            self.frame,
            text="B",
            style="TLabel",
        ).pack(side=tk.LEFT)

        # Bind to entry changes - trigger on Return, FocusOut, and key releases
        self.entry_min.bind("<Return>", self._on_entry_change)
        self.entry_min.bind("<FocusOut>", self._on_entry_change)
        self.entry_min.bind("<KeyRelease>", self._on_entry_change_delayed)

        self.entry_max.bind("<Return>", self._on_entry_change)
        self.entry_max.bind("<FocusOut>", self._on_entry_change)
        self.entry_max.bind("<KeyRelease>", self._on_entry_change_delayed)

        self.btn_presets = ttk.Menubutton(
            self.frame,
            text="Presets",
            style="TButton",
        )
        self.btn_presets.pack(side=tk.LEFT, padx=10)

        preset_menu = tk.Menu(self.btn_presets, tearoff=0)
        preset_menu.add_command(
            label="3B - 8B (Small)", command=lambda: self._set_preset(3, 8)
        )
        preset_menu.add_command(
            label="12B - 32B (Medium)", command=lambda: self._set_preset(12, 32)
        )
        preset_menu.add_command(
            label="32B - 70B (Large)", command=lambda: self._set_preset(32, 70)
        )
        preset_menu.add_command(
            label="70B - 150B (XL)", command=lambda: self._set_preset(70, 150)
        )
        preset_menu.add_separator()
        preset_menu.add_command(
            label="All (1B - 2T)", command=lambda: self._set_preset(1, 2000)
        )
        self.btn_presets.config(menu=preset_menu)

        self._update_from_entries()

        # Debounce timer for delayed updates
        self._after_id = None

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _set_preset(self, min_val: int, max_val: int):
        self.entry_min.delete(0, tk.END)
        self.entry_min.insert(0, str(min_val))
        self.entry_max.delete(0, tk.END)
        self.entry_max.insert(0, str(max_val))
        self._on_entry_change()

    def _on_entry_change_delayed(self, event=None):
        """Handle key release with debounce for immediate feedback"""
        if self._after_id:
            self.parent.after_cancel(self._after_id)
        # Schedule update after 300ms of no typing
        self._after_id = self.parent.after(300, self._on_entry_change)

    def _on_entry_change(self, event=None):
        """Called when entry values change"""
        try:
            min_val = int(self.entry_min.get())
            max_val = int(self.entry_max.get())

            # Validate and clamp values
            if min_val < 1:
                min_val = 1
                self.entry_min.delete(0, tk.END)
                self.entry_min.insert(0, "1")
            if max_val > 2000:
                max_val = 2000
                self.entry_max.delete(0, tk.END)
                self.entry_max.insert(0, "2000")

            # Ensure min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val
                self.entry_min.delete(0, tk.END)
                self.entry_min.insert(0, str(min_val))
                self.entry_max.delete(0, tk.END)
                self.entry_max.insert(0, str(max_val))

        except ValueError:
            return  # Ignore invalid input during typing

        # Notify callback if set
        if self.on_change_callback:
            self.on_change_callback()

    def _update_from_entries(self):
        try:
            min_val = int(self.entry_min.get())
            max_val = int(self.entry_max.get())
            if min_val > max_val:
                self.entry_max.delete(0, tk.END)
                self.entry_max.insert(0, str(min_val))
        except ValueError:
            pass

    def set(self, min_val: int, max_val: int):
        self.entry_min.delete(0, tk.END)
        self.entry_min.insert(0, str(min_val))
        self.entry_max.delete(0, tk.END)
        self.entry_max.insert(0, str(max_val))
        # Trigger callback when preset is set
        if self.on_change_callback:
            self.on_change_callback()

    def get(self) -> tuple:
        try:
            min_val = int(self.entry_min.get())
            max_val = int(self.entry_max.get())
            min_val = max(1, min_val)
            max_val = min(2000, max_val)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return (min_val, max_val)
        except ValueError:
            return (12, 64)


class ModelDetailsPanel:
    """Panel showing model details and score breakdown"""

    def __init__(self, parent):
        self.parent = parent
        self.current_model: Optional[ModelInfo] = None

        self.frame = ttk.Frame(parent, style="Secondary.TFrame")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_header()
        self._build_details()
        self._build_score_breakdown()

    def _build_header(self):
        header_frame = ttk.Frame(self.frame, style="Secondary.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_title = ttk.Label(
            header_frame,
            text="Model Details",
            style="Title.TLabel",
            font=("Segoe UI", 12, "bold"),
        )
        self.lbl_title.pack(anchor=tk.W)

    def _build_details(self):
        details_frame = ttk.LabelFrame(
            self.frame,
            text="Information",
            style="Secondary.TFrame",
        )
        details_frame.pack(fill=tk.X, pady=5)

        self.lbl_model_id = self._create_detail_label(details_frame, "Model ID:")
        self.lbl_author = self._create_detail_label(details_frame, "Author:")
        self.lbl_size = self._create_detail_label(details_frame, "Size:")
        self.lbl_downloads = self._create_detail_label(details_frame, "Downloads:")
        self.lbl_likes = self._create_detail_label(details_frame, "Likes:")
        self.lbl_updated = self._create_detail_label(details_frame, "Updated:")
        self.lbl_url = self._create_detail_label(details_frame, "URL:")

    def _create_detail_label(self, parent, label_text: str) -> ttk.Label:
        row = ttk.Frame(parent, style="Secondary.TFrame")
        row.pack(fill=tk.X, padx=5, pady=2)

        lbl = ttk.Label(
            row,
            text=label_text,
            style="Subtitle.TLabel",
            width=10,
            font=("Segoe UI", 9),
        )
        lbl.pack(side=tk.LEFT)

        value_lbl = ttk.Label(
            row,
            text="-",
            style="TLabel",
            font=("Consolas", 9),
        )
        value_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return value_lbl

    def _build_score_breakdown(self):
        score_frame = ttk.LabelFrame(
            self.frame,
            text="Score Breakdown",
            style="Secondary.TFrame",
        )
        score_frame.pack(fill=tk.X, pady=5)

        self.lbl_score = self._create_detail_label(score_frame, "Score:")
        self.lbl_norm_dl = self._create_detail_label(score_frame, "Norm DLs:")
        self.lbl_norm_lk = self._create_detail_label(score_frame, "Norm Likes:")
        self.lbl_time_boost = self._create_detail_label(score_frame, "Time Boost:")
        self.lbl_calculated = self._create_detail_label(score_frame, "Formula:")

    def _create_detail_label(self, parent, label_text: str) -> ttk.Label:
        row = ttk.Frame(parent, style="Secondary.TFrame")
        row.pack(fill=tk.X, padx=5, pady=2)

        lbl = ttk.Label(
            row,
            text=label_text,
            style="Subtitle.TLabel",
            width=10,
        )
        lbl.pack(side=tk.LEFT)

        value_lbl = ttk.Label(
            row,
            text="-",
            style="TLabel",
            font=("Consolas", 9),
        )
        value_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return value_lbl

    def update(self, model: Optional[ModelInfo]):
        self.current_model = model

        if model is None:
            self._clear_all()
            return

        self.lbl_model_id.config(text=model.name if "/" in model.id else model.id)
        self.lbl_author.config(text=model.author)
        self.lbl_size.config(
            text=f"{model.parsed_params_b:.1f}B"
            if model.parsed_params_b > 0
            else "Unknown"
        )
        self.lbl_downloads.config(text=f"{model.downloads:,}")
        self.lbl_likes.config(text=f"{model.likes:,}")
        self.lbl_updated.config(text=self._format_timestamp(model.timestamp))
        self.lbl_url.config(text=model.hf_url, foreground=AppStyle.ACCENT)

        if hasattr(model, "combined_score"):
            score = model.combined_score
            time_boost = self._calculate_time_boost(model.timestamp)
            self.lbl_score.config(text=f"{score:.4f}")
            self.lbl_norm_dl.config(
                text=f"{min(1.0, math.log10(model.downloads + 1) / 7.0):.3f}"
            )
            self.lbl_norm_lk.config(
                text=f"{min(1.0, math.log10(model.likes + 1) / 4.0):.3f}"
            )
            self.lbl_time_boost.config(
                text=f"{time_boost:.2f}" + (" (fresh)" if time_boost >= 0.9 else "")
            )
            self.lbl_calculated.config(
                text="0.25xNormDL + 0.6xNormLK + 0.15xTime",
                foreground=AppStyle.SUCCESS,
            )
        else:
            self.lbl_score.config(text="-")
            self.lbl_norm_dl.config(text="-")
            self.lbl_norm_lk.config(text="-")
            self.lbl_time_boost.config(text="-")
            self.lbl_calculated.config(text="-")

    def _calculate_time_boost(self, timestamp: datetime) -> float:
        delta = datetime.now(timezone.utc) - timestamp
        hours = delta.total_seconds() / 3600.0

        if hours < 24:
            return 1.0
        elif hours < 168:
            return 0.9
        elif hours < 720:
            return 0.7
        elif hours < 2160:
            return 0.5
        else:
            return 0.2

    def _format_timestamp(self, dt: datetime) -> str:
        delta = datetime.now(timezone.utc) - dt
        total_seconds = delta.total_seconds()
        hours = total_seconds / 3600.0
        days = total_seconds / 86400.0

        if hours < 1:
            minutes = total_seconds / 60.0
            return f"{int(minutes)}m ago" if minutes >= 1 else "Just now"
        elif hours < 24:
            return f"{int(hours)}h ago"
        elif days < 30:
            return f"{int(days)}d ago"
        else:
            return f"{int(days // 30)}mo ago"

    def _clear_all(self):
        for lbl in [
            self.lbl_model_id,
            self.lbl_author,
            self.lbl_size,
            self.lbl_downloads,
            self.lbl_likes,
            self.lbl_updated,
            self.lbl_url,
            self.lbl_score,
            self.lbl_norm_dl,
            self.lbl_norm_lk,
            self.lbl_time_boost,
            self.lbl_calculated,
        ]:
            lbl.config(text="-")


class ModelExplorerApp:
    """Main GUI Application"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("HuggingFace Model Explorer - GGUF Models")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 600)

        self.root.configure(bg=AppStyle.BG_PRIMARY)

        self.ranker = GGUFModelRanker()
        self.models: List[ModelInfo] = []
        self.filtered_models: List[ModelInfo] = []  # Cache for filtered results
        self.is_loading = False
        self.filter_queue = queue.Queue()  # Queue for filter operations
        self.filter_thread = None
        self.filter_lock = threading.Lock()

        self._setup_styles()
        self._build_ui()
        self._setup_bindings()

        # Start background filter processor
        self._start_filter_processor()

        self._load_data_async()

    def _start_filter_processor(self):
        """Start background thread for processing filter operations"""
        def process_filters():
            while True:
                try:
                    # Get filter request from queue (blocking)
                    filter_params = self.filter_queue.get(timeout=0.1)
                    if filter_params is None:  # Shutdown signal
                        break

                    # Process the filter
                    self._process_filter_operation(filter_params)
                    self.filter_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[FILTER ERROR] {e}")

        self.filter_thread = threading.Thread(target=process_filters, daemon=True)
        self.filter_thread.start()

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=AppStyle.BG_SECONDARY, fg=AppStyle.FG_PRIMARY)

        file_menu = tk.Menu(
            menubar, tearoff=0, bg=AppStyle.BG_TERTIARY, fg=AppStyle.FG_PRIMARY
        )
        file_menu.add_command(
            label="Refresh Data",
            command=self._refresh_data,
            accelerator="Ctrl+R",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export to CSV...",
            command=self._export_csv,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit",
            command=self._on_close,
            accelerator="Alt+F4",
        )
        menubar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(
            menubar, tearoff=0, bg=AppStyle.BG_TERTIARY, fg=AppStyle.FG_PRIMARY
        )
        view_menu.add_command(
            label="Reset Filters",
            command=self._reset_all_filters,
            accelerator="Ctrl+Shift+R",
        )
        view_menu.add_separator()
        view_menu.add_radiobutton(
            label="Show 25 models",
            value=25,
            variable=self.top_n_var,
            command=self._on_top_n_change,
        )
        view_menu.add_radiobutton(
            label="Show 50 models",
            value=50,
            variable=self.top_n_var,
            command=self._on_top_n_change,
        )
        view_menu.add_radiobutton(
            label="Show 100 models",
            value=100,
            variable=self.top_n_var,
            command=self._on_top_n_change,
        )
        view_menu.add_radiobutton(
            label="Show 200 models",
            value=200,
            variable=self.top_n_var,
            command=self._on_top_n_change,
        )
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(
            menubar, tearoff=0, bg=AppStyle.BG_TERTIARY, fg=AppStyle.FG_PRIMARY
        )
        help_menu.add_command(
            label="Keyboard Shortcuts",
            command=self._show_shortcuts,
        )
        help_menu.add_command(
            label="About",
            command=self._show_about,
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _export_csv(self):
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="hf_models_export.csv",
        )
        if not file_path:
            return

        try:
            import csv

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "#",
                        "Model ID",
                        "Author",
                        "Size (B)",
                        "Downloads",
                        "Likes",
                        "Score",
                        "Updated",
                    ]
                )

                for i, model in enumerate(self.models, 1):
                    score = (
                        model.combined_score if hasattr(model, "combined_score") else 0
                    )
                    writer.writerow(
                        [
                            i,
                            model.id,
                            model.author,
                            model.parsed_params_b if model.parsed_params_b else 0,
                            model.downloads,
                            model.likes,
                            f"{score:.4f}",
                            model.timestamp.isoformat(),
                        ]
                    )

            self.lbl_status.config(text=f"Exported to: {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{str(e)}")

    def _reset_all_filters(self):
        """Reset all filters including min likes"""
        self.slider.set(12, 64)
        self.sort_var.set("smart")
        self.search_var.set("")
        self.top_n_var.set(50)
        self.chk_var.set(0)
        self.min_likes_var.set("0")  # Reset min likes
        self._queue_filter_update()

    def _show_shortcuts(self):
        shortcuts_text = """
Keyboard Shortcuts
==================

Ctrl + F         Focus search box
Ctrl + R         Refresh data
Ctrl + C         Copy selected model ID
Ctrl + Shift+R   Reset all filters
Enter            Open model URL (browser)
Double-click     Open model URL (browser)
Right-click      Context menu

Mouse Wheel      Scroll through models
        """.strip()

        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("300x350")
        dialog.configure(bg=AppStyle.BG_PRIMARY)
        dialog.transient(self.root)
        dialog.grab_set()

        text_widget = tk.Text(
            dialog,
            bg=AppStyle.BG_SECONDARY,
            fg=AppStyle.FG_PRIMARY,
            font=("Consolas", 10),
            wrap=tk.WORD,
            padx=20,
            pady=20,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, shortcuts_text)
        text_widget.config(state=tk.DISABLED)

        btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        btn.pack(pady=10)

        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.bind("<Return>", lambda e: dialog.destroy())

    def _show_about(self):
        messagebox.showinfo(
            "About",
            "HuggingFace Model Explorer\n\n"
            "Version: 1.0\n"
            "Author: AI Reasoning Lab\n\n"
            "A beautiful GUI for browsing and ranking\n"
            "GGUF models from HuggingFace.\n\n"
            "Based on hf_best_models.py ranking logic.",
        )

    def _setup_styles(self):
        self.style = ttk.Style()
        AppStyle.configure_styles(self.style)

    def _build_ui(self):
        """Build the main UI"""
        self._build_header()
        self._build_control_panel()
        self._build_main_content()
        self._build_status_bar()
        self._build_help_tooltip()

    def _build_header(self):
        header_frame = ttk.Frame(self.root, style="Primary.TFrame")
        header_frame.pack(fill=tk.X, padx=15, pady=(15, 10))

        title_font = Font(family="Segoe UI", size=16, weight="bold")
        title_lbl = ttk.Label(
            header_frame,
            text="🤗 HuggingFace Model Explorer",
            style="TLabel",
            font=title_font,
            foreground=AppStyle.ACCENT,
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = ttk.Label(
            header_frame,
            text="Browse and rank GGUF models",
            style="Subtitle.TLabel",
        )
        subtitle_lbl.pack(side=tk.LEFT, padx=(15, 0))

    def _build_control_panel(self):
        control_frame = ttk.Frame(self.root, style="Secondary.TFrame")
        control_frame.pack(fill=tk.X, padx=15, pady=5)

        row1 = ttk.Frame(control_frame, style="Secondary.TFrame")
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            row1,
            text="Parameters:",
            style="TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.slider = CustomRangeSlider(
            row1,
            min_val=12,
            max_val=64,
            on_change_callback=self._queue_filter_update
        )
        self.slider.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            row1,
            text="Reset Range",
            command=self._reset_range,
            style="TButton",
        ).pack(side=tk.LEFT, padx=10)

        ttk.Separator(row1, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=20, pady=5
        )

        ttk.Label(
            row1,
            text="Sort by:",
            style="TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.sort_var = tk.StringVar(value="smart")
        sort_options = [
            ("Smart (Combined)", "smart"),
            ("Trending", "trending"),
            ("Likes", "likes"),
            ("Downloads", "downloads"),
            ("Modified", "modified"),
        ]

        for text, value in sort_options:
            rb = ttk.Radiobutton(
                row1,
                text=text,
                value=value,
                variable=self.sort_var,
                command=self._on_sort_change,
                style="TRadiobutton",
            )
            rb.pack(side=tk.LEFT, padx=5)

        ttk.Separator(row1, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=20, pady=5
        )

        self.btn_refresh = ttk.Button(
            row1,
            text="🔄 Refresh",
            command=self._refresh_data,
            style="Accent.TButton",
        )
        self.btn_refresh.pack(side=tk.RIGHT, padx=5)

        row2 = ttk.Frame(control_frame, style="Secondary.TFrame")
        row2.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            row2,
            text="Search:",
            style="TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)

        self.entry_search = ttk.Entry(
            row2,
            textvariable=self.search_var,
            width=40,
            font=("Consolas", 10),
        )
        self.entry_search.pack(side=tk.LEFT, padx=5)

        self.btn_clear_search = ttk.Button(
            row2,
            text="Clear",
            command=self._clear_search,
            style="TButton",
        )
        self.btn_clear_search.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            row2,
            text="Top N:",
            style="TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(20, 10))

        self.top_n_var = tk.IntVar(value=50)
        self.top_n_combo = ttk.Combobox(
            row2,
            textvariable=self.top_n_var,
            values=[25, 50, 100, 150, 200],
            state="readonly",
            width=8,
            font=("Consolas", 10),
        )
        self.top_n_combo.pack(side=tk.LEFT, padx=5)
        self.top_n_combo.bind("<<ComboboxSelected>>", self._on_top_n_change)

        self.chk_var = tk.IntVar(value=0)
        self.chk_gguf = ttk.Checkbutton(
            row2,
            text="GGUF Only (Author + GGUF Tag)",
            variable=self.chk_var,
            command=self._on_filter_change,
        )
        self.chk_gguf.pack(side=tk.LEFT, padx=20)

        # NEW: Minimum Likes Filter
        ttk.Separator(row2, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=15, pady=5
        )

        ttk.Label(
            row2,
            text="Min Likes:",
            style="TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.min_likes_var = tk.StringVar(value="0")
        self.min_likes_var.trace_add("write", self._on_min_likes_change)

        self.entry_min_likes = ttk.Entry(
            row2,
            textvariable=self.min_likes_var,
            width=8,
            font=("Consolas", 10),
        )
        self.entry_min_likes.pack(side=tk.LEFT, padx=5)

        # Preset buttons for common like thresholds
        likes_menu_btn = ttk.Menubutton(
            row2,
            text="Presets",
            style="TButton",
        )
        likes_menu_btn.pack(side=tk.LEFT, padx=5)

        likes_menu = tk.Menu(likes_menu_btn, tearoff=0)
        likes_menu.add_command(label="Any (0)", command=lambda: self._set_min_likes(0))
        likes_menu.add_command(label="Popular (100+)", command=lambda: self._set_min_likes(100))
        likes_menu.add_command(label="Very Popular (500+)", command=lambda: self._set_min_likes(500))
        likes_menu.add_command(label="Top Tier (1000+)", command=lambda: self._set_min_likes(1000))
        likes_menu.add_command(label="Elite (5000+)", command=lambda: self._set_min_likes(5000))
        likes_menu_btn.config(menu=likes_menu)

    def _on_min_likes_change(self, *args):
        """Handle minimum likes filter change"""
        self._queue_filter_update()

    def _set_min_likes(self, value: int):
        """Set minimum likes from preset"""
        self.min_likes_var.set(str(value))

    def _build_main_content(self):
        content_frame = ttk.Frame(self.root, style="Primary.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        tree_frame = ttk.Frame(content_frame, style="Secondary.TFrame")
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = (
            "#",
            "Model",
            "Author",
            "Size",
            "Downloads",
            "Likes",
            "Score",
            "Updated",
        )
        column_widths = {
            "#": 40,
            "Model": 350,
            "Author": 100,
            "Size": 60,
            "Downloads": 90,
            "Likes": 70,
            "Score": 60,
            "Updated": 80,
        }

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Treeview",
            selectmode="browse",
        )

        for col in columns:
            self.tree.heading(
                col,
                text=col,
                command=lambda c=col: self._sort_treeview(c),
            )
            self.tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)

        self.tree.column("Model", anchor=tk.W)

        scrollbar_y = ttk.Scrollbar(
            tree_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
            style="Vertical.TScrollbar",
        )
        scrollbar_x = ttk.Scrollbar(
            tree_frame,
            orient=tk.HORIZONTAL,
            command=self.tree.xview,
            style="Vertical.TScrollbar",
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.details_panel = ModelDetailsPanel(content_frame)
        self.details_panel.frame.configure(width=300)
        self.details_panel.frame.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root, style="Status.TFrame")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = ttk.Label(
            status_frame,
            text="Initializing...",
            style="Status.TLabel",
            anchor=tk.W,
            foreground=AppStyle.WARNING,
        )
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        self.lbl_count = ttk.Label(
            status_frame,
            text="Loading...",
            style="Status.TLabel",
            foreground=AppStyle.ACCENT,
        )
        self.lbl_count.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=200,
        )
        self.progress.pack(side=tk.RIGHT, padx=10)

    def _build_help_tooltip(self):
        help_frame = ttk.Frame(self.root, style="Status.TFrame")
        help_frame.pack(fill=tk.X, side=tk.BOTTOM)

        shortcuts = [
            ("Ctrl+F", "Search"),
            ("Ctrl+R", "Refresh"),
            ("Ctrl+C", "Copy selected ID"),
            ("Enter/Double-click", "Open URL"),
            ("Right-click", "Context menu"),
        ]

        for i, (key, desc) in enumerate(shortcuts):
            if i > 0:
                sep = ttk.Label(help_frame, text="|", style="Status.TLabel")
                sep.pack(side=tk.LEFT, padx=5)

            lbl = ttk.Label(
                help_frame,
                text=f"{key} = {desc}",
                style="Status.TLabel",
                foreground=AppStyle.FG_SECONDARY,
            )
            lbl.pack(side=tk.LEFT)

        self._build_menu()

    def _setup_bindings(self):
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Return>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        self.tree.bind("<Button-2>", self._on_tree_right_click)

        self.root.bind("<Control-f>", lambda e: self.entry_search.focus_set())
        self.root.bind("<Control-r>", lambda e: self._refresh_data())
        self.root.bind("<Control-c>", self._on_copy_selection)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_copy_selection(self, event=None):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item["values"]
            if len(values) > 1:
                model_id = values[1]
                pyperclip.copy(model_id)
                self.lbl_status.config(text=f"Copied: {model_id}")

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            model_id = item["values"][1] if len(item["values"]) > 1 else None

            for model in self.filtered_models:  # Use filtered_models instead
                if model.id == model_id:
                    size_info = (
                        f"{model.parsed_params_b:.1f}B"
                        if model.parsed_params_b
                        else "?"
                    )
                    print(f"[DEBUG] Selected: {model_id} | Size: {size_info}")
                    self.details_panel.update(model)
                    break

    def _on_tree_double_click(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            model_id = item["values"][1] if len(item["values"]) > 1 else None

            if model_id:
                for model in self.filtered_models:  # Use filtered_models
                    if model.id == model_id:
                        webbrowser.open(model.hf_url)
                        break

    def _on_tree_right_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        model_id = item["values"][1] if len(item["values"]) > 1 else None

        if model_id:
            context_menu = tk.Menu(self.root, tearoff=0, bg=AppStyle.BG_SECONDARY)

            def copy_id():
                pyperclip.copy(model_id)
                self.lbl_status.config(text=f"Copied: {model_id}")

            def copy_url():
                for model in self.filtered_models:
                    if model.id == model_id:
                        pyperclip.copy(model.hf_url)
                        self.lbl_status.config(text=f"Copied URL: {model.hf_url}")
                        break

            def open_url():
                for model in self.filtered_models:
                    if model.id == model_id:
                        webbrowser.open(model.hf_url)
                        break

            context_menu.add_command(label="Copy Model ID", command=copy_id)
            context_menu.add_command(label="Copy URL", command=copy_url)
            context_menu.add_separator()
            context_menu.add_command(label="Open in Browser", command=open_url)

            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def _on_sort_change(self):
        self._queue_filter_update()

    def _on_search_change(self, *args):
        self._queue_filter_update()

    def _on_filter_change(self):
        self._queue_filter_update()

    def _on_top_n_change(self, event=None):
        self._queue_filter_update()

    def _reset_range(self):
        self.slider.set(12, 64)
        self._queue_filter_update()

    def _clear_search(self):
        self.search_var.set("")
        self.entry_search.focus_set()

    def _queue_filter_update(self):
        """Queue a filter update operation (non-blocking)"""
        if not self.models:
            return

        # Parse min likes
        try:
            min_likes = int(self.min_likes_var.get())
            if min_likes < 0:
                min_likes = 0
        except ValueError:
            min_likes = 0

        # Get current filter parameters
        filter_params = {
            'min_b': self.slider.get()[0],
            'max_b': self.slider.get()[1],
            'sort_mode': self.sort_var.get(),
            'search_query': self.search_var.get().lower().strip(),
            'top_n': self.top_n_var.get(),
            'gguf_only': self.chk_var.get() == 1,
            'min_likes': min_likes,  # NEW: Add min likes to filter params
        }

        # Put in queue for background processing
        try:
            # Clear old items
            while not self.filter_queue.empty():
                try:
                    self.filter_queue.get_nowait()
                except queue.Empty:
                    break
            self.filter_queue.put(filter_params)
        except Exception as e:
            print(f"[QUEUE ERROR] {e}")

    def _process_filter_operation(self, params):
        """Process filter operation in background thread"""
        try:
            min_b = params['min_b']
            max_b = params['max_b']
            sort_mode = params['sort_mode']
            search_query = params['search_query']
            top_n = params['top_n']
            gguf_only = params['gguf_only']
            min_likes = params.get('min_likes', 0)  # NEW: Get min likes

            # Filter models
            filtered = []
            for model in self.models:
                size = model.parsed_params_b

                if size is not None and size > 0:
                    if size < min_b or size > max_b:
                        continue

                # NEW: Filter by minimum likes
                if model.likes < min_likes:
                    continue

                if search_query:
                    name = model.name.lower()
                    author = model.author.lower()
                    if search_query not in name and search_query not in author:
                        continue

                if gguf_only:
                    from config import GGUF_KINGS
                    if model.author.lower() not in [k.lower() for k in GGUF_KINGS]:
                        continue
                    if not self._is_gguf_model(model):
                        continue

                filtered.append(model)

            # Sort with smart multi-level sorting
            sorted_models = self._sort_models_smart(filtered, sort_mode)
            displayed_models = sorted_models[:top_n]

            # Update UI from main thread
            self.root.after(0, lambda: self._update_ui_after_filter(
                displayed_models, len(filtered), params
            ))

        except Exception as e:
            print(f"[FILTER PROCESS ERROR] {e}")

    def _update_ui_after_filter(self, displayed_models, total_filtered, params):
        """Update UI after filter operation completes"""
        self.filtered_models = displayed_models  # Cache for selection

        # Update treeview
        self._update_treeview(displayed_models)

        # Update status
        min_b = params['min_b']
        max_b = params['max_b']
        sort_mode = params['sort_mode']
        search_query = params['search_query']
        gguf_only = params['gguf_only']
        top_n = params['top_n']
        min_likes = params.get('min_likes', 0)  # NEW

        total_models = len(self.models)
        range_passed = len([m for m in self.models
                            if m.parsed_params_b and min_b <= m.parsed_params_b <= max_b])

        status_msg = f"Displayed: {len(displayed_models)} | Range: {range_passed}/{total_models} | Sort: {sort_mode}"
        if gguf_only:
            status_msg += " | GGUF Only"
        if search_query:
            status_msg += f' | Q: "{search_query}"'
        if min_likes > 0:  # NEW
            status_msg += f' | ❤️ >{min_likes}'

        self.lbl_count.config(text=status_msg)

        # Log filter operation
        logging.info(
            "FILTER_APPLIED",
            extra={
                "total_models_before": total_models,
                "models_after_size_filter": total_filtered,
                "models_displayed": len(displayed_models),
                "min_size_b": min_b,
                "max_size_b": max_b,
                "min_likes": min_likes,  # NEW
                "search_query": search_query or None,
                "sort_mode": sort_mode,
                "top_n": top_n,
                "gguf_only": gguf_only,
                "sample_model_ids": [m.id for m in displayed_models[:3]] if displayed_models else [],
            },
        )

    def _load_data_async(self):
        self.is_loading = True
        self.btn_refresh.config(state=tk.DISABLED)
        self.progress.start()
        self.lbl_status.config(text="Loading models...")

        thread = threading.Thread(target=self._load_data_thread, daemon=True)
        thread.start()

    def _load_data_thread(self):
        try:
            self.ranker.prepare_data()
            self.models = self.ranker.get_ranked_list(
                RankingMode.STABLE,
                min_b=None,
                max_b=None,
                top_n=5000,
            )

            self.root.after(0, self._on_data_loaded)
        except Exception as e:
            self.root.after(0, lambda: self._on_data_error(str(e)))

    def _on_data_loaded(self):
        self.is_loading = False
        self.btn_refresh.config(state=tk.NORMAL)
        self.progress.stop()

        unknown_count = sum(
            1 for m in self.models if m.parsed_params_b is None or m.parsed_params_b == 0
        )

        logging.info(
            "DATA_LOADED",
            extra={
                "total_models": len(self.models),
                "unknown_sizes": unknown_count,
                "model_ids_sample": [m.id for m in self.models[:5]] if self.models else [],
                "source": "HuggingFace API",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        if unknown_count > 0:
            self.lbl_status.config(
                text=f"Loaded {len(self.models)} models ({unknown_count} unknown params)...",
                foreground=AppStyle.WARNING,
            )
            self.root.update()
            # Fetch unknown params in background
            threading.Thread(target=self._fetch_unknown_params_async, daemon=True).start()
        else:
            self.lbl_status.config(
                text=f"Loaded {len(self.models)} models", foreground=AppStyle.SUCCESS
            )

        # Apply initial filter
        self._queue_filter_update()

    def _fetch_unknown_params_async(self):
        """Fetch unknown parameters in background without blocking GUI"""
        import requests

        unknown_gguf = [
            m
            for m in self.models
            if (m.parsed_params_b is None or m.parsed_params_b == 0)
               and self._is_gguf_model(m)
        ]

        if not unknown_gguf:
            return

        print(f"[INFO] Fetching params for {len(unknown_gguf)} GGUF models...")
        cache = self.ranker._params_cache
        fetched_count = 0

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
        )

        for model in unknown_gguf[:200]:
            try:
                params = None

                resp = session.get(
                    f"https://huggingface.co/api/models/{model.id}",
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()

                    gguf = data.get("gguf")
                    if gguf and isinstance(gguf, dict):
                        total = gguf.get("total")
                        if total and isinstance(total, (int, float)):
                            params = total / 1e9

                if params and params > 0.5 and params < 2000:
                    model.parsed_params_b = params
                    cache.set_model_params(model.id, params)
                    fetched_count += 1
                    print(f"  [OK] {model.id}: {params:.1f}B")
                else:
                    if gguf:
                        print(f"  [SKIP] {model.id}: gguf={gguf}")
                    else:
                        print(f"  [SKIP] {model.id}: no gguf field")

            except Exception as e:
                print(f"  [ERR] {model.id}: {e}")

        session.close()

        print(
            f"[INFO] Fetched {fetched_count}/{min(len(unknown_gguf), 200)} GGUF models"
        )

        if fetched_count > 0:
            # Refresh UI after fetching params
            self.root.after(0, self._queue_filter_update)

    def _on_data_error(self, error_msg):
        self.is_loading = False
        self.btn_refresh.config(state=tk.NORMAL)
        self.progress.stop()

        self.lbl_status.config(
            text=f"Error: {error_msg[:50]}", foreground=AppStyle.ERROR
        )
        print(f"[ERROR] {error_msg}")

    def _refresh_data(self):
        self.models = []
        self.filtered_models = []
        self._load_data_async()

    def _is_gguf_model(self, model: ModelInfo) -> bool:
        """Check if model is GGUF format by tags or name"""
        model_lower = model.id.lower()

        gguf_patterns = ["gguf", "-gguf"]

        if any(pattern in model_lower for pattern in gguf_patterns):
            return True

        for tag in model.tags:
            if "gguf" in tag.lower():
                return True

        return False

    def _sort_models_smart(self, models: List[ModelInfo], sort_mode: str) -> List[ModelInfo]:
        """
        Smart multi-level sorting.
        Primary sort by selected mode, then by likes, then by downloads.
        Trending mode uses single-level sort (downloads, likes).
        """
        if sort_mode == "trending":
            # Trending: simple multi-level (downloads, likes)
            return sorted(models, key=lambda m: (m.downloads, m.likes), reverse=True)

        elif sort_mode == "likes":
            # Primary: likes, Secondary: downloads, Tertiary: modified (timestamp)
            return sorted(models, key=lambda m: (
                m.likes,
                m.downloads,
                m.timestamp.timestamp() if m.timestamp else 0
            ), reverse=True)

        elif sort_mode == "downloads":
            # Primary: downloads, Secondary: likes, Tertiary: modified
            return sorted(models, key=lambda m: (
                m.downloads,
                m.likes,
                m.timestamp.timestamp() if m.timestamp else 0
            ), reverse=True)

        elif sort_mode == "modified":
            # Primary: modified, Secondary: likes, Tertiary: downloads
            return sorted(models, key=lambda m: (
                m.timestamp.timestamp() if m.timestamp else 0,
                m.likes,
                m.downloads
            ), reverse=True)

        elif sort_mode == "smart":
            # Smart: calculate combined score, then sort by score
            for m in models:
                m.combined_score = self._calculate_smart_score(m)
            return sorted(models, key=lambda m: m.combined_score, reverse=True)
        else:
            return models

    def _calculate_smart_score(self, m: ModelInfo) -> float:
        norm_dl = min(1.0, math.log10(m.downloads + 1) / 7.0)
        norm_lk = min(1.0, math.log10(m.likes + 1) / 4.0)
        time_boost = self._calculate_time_boost(m.timestamp)
        return (0.25 * norm_dl) + (0.6 * norm_lk) + (0.15 * time_boost)

    def _calculate_time_boost(self, timestamp: datetime) -> float:
        delta = datetime.now(timezone.utc) - timestamp
        hours = delta.total_seconds() / 3600.0

        if hours < 24:
            return 1.0
        elif hours < 168:
            return 0.9
        elif hours < 720:
            return 0.7
        elif hours < 2160:
            return 0.5
        else:
            return 0.2

    def _update_treeview(self, models: List[ModelInfo]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, model in enumerate(models, 1):
            score_text = (
                f"{model.combined_score:.3f}"
                if hasattr(model, "combined_score")
                else "-"
            )

            downloads_text = self._format_number(model.downloads)
            likes_text = str(model.likes)

            size_text = (
                f"{model.parsed_params_b:.1f}B"
                if model.parsed_params_b and model.parsed_params_b > 0
                else "?"
            )

            updated_text = self._format_timestamp(model.timestamp)

            self.tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    model.id,
                    model.author,
                    size_text,
                    downloads_text,
                    likes_text,
                    score_text,
                    updated_text,
                ),
            )

        self.lbl_count.config(text=f"Showing {len(models)} models")

    def _format_number(self, num: int) -> str:
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)

    def _format_timestamp(self, dt: datetime) -> str:
        delta = datetime.now(timezone.utc) - dt
        total_seconds = delta.total_seconds()
        hours = total_seconds / 3600.0
        days = total_seconds / 86400.0

        if hours < 1:
            minutes = total_seconds / 60.0
            return f"{int(minutes)}m" if minutes >= 1 else "now"
        elif hours < 24:
            return f"{int(hours)}h"
        elif days < 30:
            return f"{int(days)}d"
        else:
            return f"{int(days // 30)}mo"

    def _sort_treeview(self, col):
        current_order = self.tree.heading(col).get("order", "asc")

        if current_order == "asc":
            new_order = "desc"
        else:
            new_order = "asc"

        self.tree.heading(col, order=new_order)

        column_indices = {
            "#": 0,
            "Model": 1,
            "Author": 2,
            "Size": 3,
            "Downloads": 4,
            "Likes": 5,
            "Score": 6,
            "Updated": 7,
        }

        idx = column_indices.get(col, 0)

        items = [
            (self.tree.item(item)["values"], item) for item in self.tree.get_children()
        ]

        def sort_key(item):
            values = item[0]
            if idx == 0:
                return values[0] if values else 0
            elif idx in (4, 5):
                return int(
                    values[idx]
                    .replace("K", "000")
                    .replace("M", "000000")
                    .replace(".", "")
                )
            elif idx == 3:
                val = values[idx]
                if val == "?":
                    return 0
                return float(val.replace("B", ""))
            elif idx == 6:
                val = values[idx]
                if val == "-":
                    return 0
                return float(val)
            else:
                return str(values[idx])

        if new_order == "asc":
            items.sort(key=sort_key)
        else:
            items.sort(key=sort_key, reverse=True)

        for index, (values, item) in enumerate(items):
            self.tree.move(item, "", index)

    def _on_close(self):
        if self.is_loading:
            if not messagebox.askyesno(
                    "Confirm",
                    "Data is still loading. Are you sure you want to exit?",
            ):
                return

        # Signal filter thread to stop
        try:
            self.filter_queue.put_nowait(None)
        except:
            pass

        self.root.destroy()


def main():
    root = tk.Tk()

    try:
        app = ModelExplorerApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Startup Error", f"Failed to start application:\n{str(e)}")
        raise


if __name__ == "__main__":
    main()