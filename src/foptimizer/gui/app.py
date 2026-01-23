#!/usr/bin/env python3

import json
import threading
from pathlib import Path
from time import perf_counter

import customtkinter as ctk
import CTkGradient as ctkg
import pywinstyles as pywin
from CTkToolTip import CTkToolTip as tip

from foptimizer.backend.logic import ALIASES
from foptimizer.backend.tools.misc import size_bytes, get_project_version, interp_hex_color

with open("config/optimizations_list.json") as opt_json:
    OPTIMIZATIONS = json.load(opt_json)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("config/ctk_theme.json")


class AppInfoFrame(ctkg.GradientFrame):
    def __init__(self, root):
        super().__init__(
            master=root,
            width=1,
            height=40,
            direction="horizontal",
            colors=("#f46b45", "#eea849"),
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self.version_label = ctk.CTkLabel(
            self,
            text=f"fOptimizer v{get_project_version()}",
            font=ctk.CTkFont(size=20, family="Calibri", weight="bold"),
            text_color="#FFFFFF",
            bg_color="#f46b45",
        )
        self.version_label.pack(expand=True)
        pywin.set_opacity(
            self.version_label, color="#f46b45"
        )  # https://github.com/TomSchimansky/CustomTkinter/discussions/2214


class FolderSelectionFrame(ctk.CTkFrame):
    def __init__(
        self, root, label: str, placeholder_text: str, tip_text: str, on_empty_text: str
    ):
        super().__init__(root, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=label)
        self.label.grid(row=0, column=0, columnspan=2, padx=10, pady=(3, 0), sticky="w")

        self.field = ctk.CTkEntry(self)
        self.field.grid(row=1, column=0, padx=(10, 5), pady=(5, 10), sticky="ew")

        self.browse_button = ctk.CTkButton(
            self,
            text="Browse",
            width=100,
            command=self.browse,
            fg_color="#292929",
            hover_color="#8a6736",
            border_color="#eea849",
            border_width=1,
        )
        self.browse_button.grid(row=1, column=1, padx=(5, 10), pady=(5, 10))
        tip(self.browse_button, "Browse the filesystem for a folder")

        self.placeholder_text = placeholder_text
        self.tip_text = tip_text
        self.on_empty_text = on_empty_text

        self.placeholder_text_color = self.field._placeholder_text_color
        self.border_color = self.field._border_color

        tip(self.field, tip_text)

    def browse(self):
        folder = ctk.filedialog.askdirectory(title="Select Folder")
        if folder:
            self.field.delete(0, "end")
            self.field.insert(0, folder)

    def get_folder(self):
        path_text = self.field.get().strip()
        return path_text if path_text != "" else None

    def on_empty(self):
        self.field.configure(
            border_color="#972222", placeholder_text=self.on_empty_text
        )
        self.after(
            2000,
            lambda: self.field.configure(
                border_color=self.border_color, placeholder_text=self.placeholder_text
            ),
        )
    
    def set_state(self, state: str):
        self.field.configure(state=state)
        self.browse_button.configure(state=state)


class ProgressWindow(ctk.CTkFrame):
    def __init__(self, root):
        super().__init__(root, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            self,
            mode="determinate",
            corner_radius=5,
            progress_color=interp_hex_color("#f46b45", "#eea849", 0),
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        self.progress_text = ctk.CTkLabel(self, text="0 of 0 files processed")
        self.progress_text.grid(row=1, column=0, padx=0, pady=(10, 0), sticky="ew")

        self.start_size = 0
        self.end_size = 0
        self.diff_size = 0
        self.total_saved = 0

        self.processed = 0
        self.total = 0

        self.start_time = 0
        self.end_time = 0
        self.perftime = 0

        self.error_text = None

    def start(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.start_size = size_bytes(input_dir)
        self.error_text = None
        self.start_time = perf_counter()

    def update(self, processed: int, total: int):
        self.processed = processed
        self.total = total
        self.progress_bar.set(self.processed / self.total if total != 0 else 0)
        self.progress_text.configure(
            text=f"{self.processed} of {self.total} files processed"
        )
        self.progress_bar.configure(
            progress_color=interp_hex_color(
                "#f46b45", "#eea849", processed / total if total != 0 else 0
            )
        )

    def complete(self, title):
        if self.error_text:
            return

        self.end_time = perf_counter()
        self.perftime = round(self.end_time - self.start_time, 2)

        if self.input_dir == self.output_dir:
            self.end_size = size_bytes(self.output_dir)
            self.diff_size = self.start_size - self.end_size
            self.total_saved += self.diff_size

            self.progress_text.configure(
                text=f"{title} completed: {self.processed} of "
                f"{self.total} files processed in {self.perftime} "
                f"seconds, saving "
                f"{round(self.diff_size / 1024**2, 1)} MB"
                f"\nTotal saved so far: "
                f"{round(self.total_saved / 1024**2, 1)} MB"
            )
        else:
            self.start_size = 0
            self.end_size = 0
            self.progress_text.configure(
                text=f"{title} completed: {self.processed} of "
                f"{self.total} files processed "
                f"in {self.perftime} seconds"
            )

    def error(self, error_text):
        self.error_text = error_text
        self.progress_text.configure(text=f"{self.error_text}")


class OptimizationOption(ctk.CTkButton):
    buttons = []
    params = []

    @staticmethod
    def set_state_all_instances(state: str):
        for btn in OptimizationOption.buttons:
            btn.configure(state=state)

    def __init__(
        self,
        root,
        key: str,
        info: dict,
        input_folder_frame,
        output_folder_frame,
        progress_window,
        optimization_window,
    ):
        super().__init__(
            root,
            text=info["name"],
            fg_color="#292929",
            hover_color="#7e3825",
            border_color="#f46b45",
            border_width=1,
            corner_radius=0,
            command=self.button_callback,
        )
        OptimizationOption.buttons.append(self)

        self.key = key
        self.info = info
        self.input_folder_frame = input_folder_frame
        self.output_folder_frame = output_folder_frame
        self.progress_window = progress_window
        self.optimization_window = optimization_window
        self.params_values = {}

        self.display_frame = ctk.CTkFrame(
            self.optimization_window, fg_color="transparent"
        )
        self.display_frame.grid(row=0, column=0, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.bind("<Configure>", self.on_resize)

        self._setup_info_ui()

    def _setup_info_ui(self):
        self.header = ctk.CTkLabel(
            self.display_frame,
            text=self.info["name"],
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.header.pack(fill="x", padx=20, pady=(20, 5))

        self.desc = ctk.CTkLabel(
            self.display_frame,
            text=self.info["description"],
            justify="left",
            anchor="w",
        )
        self.desc.pack(fill="x", padx=20, pady=10)

        self.warn = None
        if self.info["warning"]:
            self.warn = ctk.CTkLabel(
                self.display_frame,
                text=f"WARNING: {self.info['warning']}",
                justify="left",
                anchor="w",
            )
            self.warn.pack(fill="x", padx=20, pady=0)

        line = ctk.CTkFrame(self.display_frame, height=2, fg_color="#4e5255")
        line.pack(fill="x", padx=20, pady=0)

        if self.info["parameters"]:  
            self.options_header = ctk.CTkLabel(
                self.display_frame,
                text="Options",
                font=ctk.CTkFont(size=20, weight="bold"),
                anchor="w",
            )
            self.options_header.pack(fill="x", padx=20, pady=5)

            self.options_container = ctk.CTkFrame(
                self.display_frame, fg_color="transparent"
            )
            self.options_container.pack(fill="x", padx=20, pady=0)

            self.renderers = {
                "checkbox": self._build_checkbox,
                "slider": self._build_slider,
                "int_input": self._build_int_input,
            }

            for param in self.info.get("parameters", []):
                p_type = param["type"]
                if p_type in self.renderers:
                    self.renderers[p_type](param)

        self.apply_btn = ctk.CTkButton(
            self.display_frame,
            text=f"Apply Optimization: {self.info['name']}",
            height=40,
            fg_color="transparent",
            border_width=1,
            border_color="#f46b45",
            hover_color="#7e3825",
            command=self.execute_optimization,
        )
        self.apply_btn.pack(fill="x", padx=20, pady=15)

    def _build_checkbox(self, p):
        var = ctk.BooleanVar(value=p["default"])
        checkbox = ctk.CTkCheckBox(
            self.options_container,
            text=p["label"],
            variable=var,
            fg_color="#f46b45",
            hover_color="#7e3825",
            border_width=1,
        )
        checkbox.pack(anchor="w", pady=(10, 5))
        self.params_values[p["id"]] = var
        tip(checkbox, p["tip"])
        
        OptimizationOption.params.append(checkbox)

    def _build_slider(self, p):
        header_frame = ctk.CTkFrame(self.options_container, fg_color="transparent")
        header_frame.pack(fill="x")

        ctk.CTkLabel(header_frame, text=p["label"]).pack(side="left")
        
        value_label = ctk.CTkLabel(header_frame, text=str(p["default"]), text_color="#ffffff")
        value_label.pack(side="right")

        var = ctk.IntVar(value=p["default"])
        slider = ctk.CTkSlider(
            self.options_container,
            from_=p["min"],
            to=p["max"],
            variable=var,
            command=lambda e: value_label.configure(text=str(int(e))),
            button_color="#f46b45",
            button_hover_color="#7e3825",
            progress_color="#7e3825",
        )
        slider.pack(fill="x", pady=(0, 10))
        self.params_values[p["id"]] = var
        tip(slider, p["tip"])
        
        OptimizationOption.params.append(slider)
    
    def _build_int_input(self, p):
        ctk.CTkLabel(self.options_container, text=p["label"]).pack(anchor="w")

        var = ctk.StringVar(value=str(p["default"]))
        entry = ctk.CTkEntry(
            self.options_container,
            textvariable=var,
        )
        entry.pack(fill="x", pady=5)
        self.params_values[p["id"]] = var
        tip(entry, p["tip"])
        
        entry.bind("<FocusOut>", lambda e: self._validate_int_entry(var, p))
        
        OptimizationOption.params.append(entry)

    def _validate_int_entry(self, var, p):
        try:
            val = int(var.get())
        except ValueError:
            var.set(str(p["default"]))
            return

        p_min = p.get("min")
        p_max = p.get("max")
        if p_min is not None:
            val = max(p_min, val)
        if p_max is not None:
            val = min(p_max, val)

        if p.get("power_of_two"):
            if not((val > 0) and (val & (val - 1) == 0)):
                val = p["default"]

        var.set(str(val))

    def button_callback(self):
        for btn in OptimizationOption.buttons:
            btn.configure(fg_color="#292929")
        self.configure(fg_color="#7e3825")

        self.display_frame.tkraise()

    def execute_optimization(self):
        input_dir = self.input_folder_frame.get_folder()
        if not (input_dir):
            self.input_folder_frame.on_empty()
            return

        output_dir = self.output_folder_frame.get_folder()
        if not (output_dir):
            output_dir = input_dir

        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        option_params = {}
        for p_id, var in self.params_values.items():
            value = var.get()
            if isinstance(value, str) and value.isdigit():
                option_params[p_id] = int(value)
            else:
                option_params[p_id] = value

        kwargs = {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "progress_window": self.progress_window,
            **option_params,
        }

        optimization_thread = threading.Thread(
            target=ALIASES.get(self.key), kwargs=kwargs, daemon=True
        )

        self.set_state_critical(state="disabled")

        self.progress_window.start(input_dir=input_dir, output_dir=output_dir)
        optimization_thread.start()
        self.monitor_button_callback_thread(optimization_thread)

    def monitor_button_callback_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_button_callback_thread(thread))
        else:
            self.progress_window.complete(self.info["name"])
            self.set_state_critical(state="normal")

    def on_resize(self, event):
        if not self.display_frame.winfo_viewable():
            return

        target_width = event.width - 40 # 20px+20px padding

        if target_width > 0:
            self.header.configure(wraplength=target_width)
            self.desc.configure(wraplength=target_width)
            if self.warn:
                self.warn.configure(wraplength=target_width)
    
    def set_state_critical(self, state: str):
        OptimizationOption.set_state_all_instances(state=state)
        self.apply_btn.configure(state=state)
        self.input_folder_frame.set_state(state=state)
        self.output_folder_frame.set_state(state=state)
        for opt in OptimizationOption.params:
            opt.configure(state=state)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_window()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.app_frame = ctk.CTkFrame(self, corner_radius=0)
        self.app_frame.grid(sticky="nsew")
        self.app_frame.grid_columnconfigure(0, weight=0)
        self.app_frame.grid_columnconfigure(1, weight=1)
        self.app_frame.grid_rowconfigure(4, weight=1)

        self.info_frame = AppInfoFrame(self.app_frame)
        self.info_frame.grid(row=0, column=0, sticky="ew", columnspan=2)

        self.input_folder_frame = FolderSelectionFrame(
            self.app_frame,
            label="Select Input Folder",
            placeholder_text="",
            tip_text="File path to input folder",
            on_empty_text="Please select an existing input folder",
        )
        self.input_folder_frame.grid(row=1, pady=(3, 0), sticky="ew", columnspan=2)

        self.output_folder_frame = FolderSelectionFrame(
            self.app_frame,
            label="Select Output Folder",
            placeholder_text="",
            tip_text=(
                "File path to output folder\nLeave this "
                "field blank to apply changes directly"
                "to the input folder"
            ),
            on_empty_text="",
        )
        self.output_folder_frame.grid(row=2, pady=(0, 10), sticky="ew", columnspan=2)

        self.progress_window = ProgressWindow(self.app_frame)
        self.progress_window.grid(
            row=3, column=0, padx=10, pady=(10, 10), sticky="ew", columnspan=2
        )

        self.optimization_menu = ctk.CTkScrollableFrame(
            self.app_frame,
            corner_radius=0,
            scrollbar_button_color="#4e5255",
        )
        self.optimization_menu.grid(row=4, column=0, sticky="nsew")
        self.optimization_menu.grid_columnconfigure(0, weight=1)

        self.optimization_window = ctk.CTkScrollableFrame(
            self.app_frame,
            corner_radius=0,
            scrollbar_button_color="#4e5255",
        )
        self.optimization_window.grid(row=4, column=1, sticky="nsew")
        self.optimization_window.grid_columnconfigure(0, weight=1)

        for i, (key, info) in enumerate(OPTIMIZATIONS.items()):
            btn = OptimizationOption(
                root=self.optimization_menu,
                key=key,
                info=info,
                input_folder_frame=self.input_folder_frame,
                output_folder_frame=self.output_folder_frame,
                progress_window=self.progress_window,
                optimization_window=self.optimization_window,
            )

            btn.grid(row=i, sticky="ew")

        if OptimizationOption.buttons:
            OptimizationOption.buttons[0].button_callback()

    def config_window(self):
        self.title("fOptimizer")
        self.geometry(f"{self.winfo_screenwidth()//2}x{self.winfo_screenheight()//2}")
        self.iconbitmap("assets/foptimizer.ico")


def main():
    foptimizer = App()
    foptimizer.mainloop()


if __name__ == "__main__":
    main()
