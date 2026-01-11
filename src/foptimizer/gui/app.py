import threading
from pathlib import Path
from time import perf_counter
from tkinter import filedialog

import customtkinter as ctk
from CTkToolTip import CTkToolTip as tip

import foptimizer.backend.logic as backend
from foptimizer.backend.tools.misc import dir_size_bytes, get_project_version


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("assets/foptimizer-theme.json")

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600

"""
    "Name": {
        "description": "Describes the function briefly.", 
        "lossless_option": Default/None,
        "level_range" : (Minimum, Maximum, Default),
        "remove_option" : Default/None,
        "one_click" : bool,
        "function" : backend.logic_function_name,
    },
"""

OPTIMIZATIONS = {
    "Remove Duplicate VTFs": {
        "description": (
            "Collects all duplicate VTF images into a shared directory and redirects "
            "VMTs to that single VTF image."
        ),
        "lossless_option": None,
        "level_range": None,
        "remove_option": None,
        "one_click": True,
        "function": backend.logic_remove_duplicate_vtfs,
    },
    "Fit Alpha": {
        "description": (
            "Strip unnecessary channels from VTF images, 'fitting' their formats "
            "as exactly as possible."
        ),
        "lossless_option": True,
        "level_range": None,
        "remove_option": None,
        "one_click": True,
        "function": backend.logic_fit_alpha,
    },
    "Remove Redundant Files": {
        "description": "Removes files unused by both modern engine branches and modding tools.",
        "lossless_option": None,
        "level_range": None,
        "remove_option": True,
        "one_click": True,
        "function": backend.logic_remove_unused_files,
    },
    "Shrink Solid Colour VTFs": {
        "description": (
            "Shrinks all solid-colour VTFs to a minimum resolution, keeping its usage "
            "identical but filesize minimal.\nEncodes a flag to skip shrunk images."
        ),
        "lossless_option": None,
        "level_range": None,
        "remove_option": None,
        "one_click": True,
        "function": backend.logic_shrink_solid,
    },
    "Remove Unaccessed VTFs": {
        "description": (
            "Removes all VTF files not referenced by any VMT in the input folder."
            "\nWARNING: this will remove VTF images referenced only in code!"
        ),
        "lossless_option": None,
        "level_range": None,
        "remove_option": True,
        "one_click": True,
        "function": backend.logic_remove_unaccessed_vtfs,
    },
    "Halve Normals": {
        "description": (
            "Halves the dimensions of all normal map VTF images. "
            "Encodes a flag to prevent halving the same image twice."
        ),
        "lossless_option": None,
        "level_range": None,
        "remove_option": None,
        "one_click": True,
        "function": backend.logic_halve_normals,
    },
    "PNG Optimization": {
        "description": "Optimizes PNG images and strips unnecessary metadata.",
        "lossless_option": False,
        "level_range": (0, 100, 75),
        "remove_option": None,
        "one_click": True,
        "function": backend.logic_optimize_png,
    },
    "WAV to OGG": {
        "description": (
            "Converts all WAV files to OGG files, trading slight quality loss "
            "for a large filesize reduction.\nWARNING: you have to change all "
            "references to .wav files to .ogg in code and on maps!"
        ),
        "lossless_option": None,
        "level_range": (-1, 10, 10),
        "remove_option": True,
        "one_click": False,
        "function": backend.logic_wav_to_ogg,
    },
}


class FolderSelectionFrame(ctk.CTkFrame):
    def __init__(
        self, root, label: str, placeholder_text: str, tip_text: str, on_empty_text: str
    ):
        super().__init__(root)

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
            hover_color="#7e3825",
            border_color="#b65033",
            border_width=1,
        )
        self.browse_button.grid(row=1, column=1, padx=(5, 10), pady=(5, 10))

        self.placeholder_text = placeholder_text
        self.tip_text = tip_text
        self.on_empty_text = on_empty_text

        self.placeholder_text_color = self.field._placeholder_text_color
        self.border_color = self.field._border_color

        tip(self.field, tip_text)

    def browse(self):
        folder = filedialog.askdirectory(title="Select Folder")
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


class DescriptionLabel(ctk.CTkLabel):
    def __init__(self, root, default_text: str):
        super().__init__(root, text=default_text, justify="left")
        self.default_text = default_text
        self.configure(wraplength=DEFAULT_WIDTH)

    def set_description(self, text: str):
        self.configure(text=text)

    def reset_description(self):
        self.configure(text=self.default_text)


class ProgressWindow(ctk.CTkFrame):
    def __init__(self, root):
        super().__init__(root)

        self.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            self, mode="determinate", corner_radius=5, progress_color="#b65033"
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

        self.start_size = dir_size_bytes(input_dir)
        self.error_text = None
        self.start_time = perf_counter()

    def update(self, processed: int, total: int):
        self.processed = processed
        self.total = total
        self.progress_bar.set(self.processed / self.total if total != 0 else 0)
        self.progress_text.configure(
            text=f"{self.processed} of {self.total} files processed"
        )

    def complete(self):
        if self.error_text:
            return

        self.end_time = perf_counter()
        self.perftime = round(self.end_time - self.start_time, 2)

        if self.input_dir == self.output_dir:
            self.end_size = dir_size_bytes(self.output_dir)
            self.diff_size = self.start_size - self.end_size
            self.total_saved += self.diff_size

            self.progress_text.configure(
                text=f"Optimization complete: {self.processed} of "
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
                text=f"Optimization complete: {self.processed} of "
                f"{self.total} files processed "
                f"in {self.perftime} seconds"
            )

    def error(self, error_text):
        self.error_text = error_text
        self.progress_text.configure(text=f"{self.error_text}")


class OptimizationButton(ctk.CTkFrame):
    buttons = []

    @staticmethod
    def set_state_all_instances(state: str):
        for i in OptimizationButton.buttons:
            if hasattr(i, "button"):
                i.button.configure(state=state)
            if hasattr(i, "quality_slider"):
                i.quality_slider.configure(state=state)
            if hasattr(i, "lossless_check"):
                i.lossless_check.configure(state=state)
            if hasattr(i, "remove_check"):
                i.remove_check.configure(state=state)

    def __init__(
        self,
        root,
        label,
        description,
        lossless_option,
        remove_option,
        function,
        one_click,
        input_getter,
        output_getter,
        desc_widget: DescriptionLabel,
        progress_window: ProgressWindow,
        folder_selection: FolderSelectionFrame,
        level_range,
    ):
        super().__init__(root)

        OptimizationButton.buttons.append(self)

        self.label = label
        self.description = description
        self.lossless_option = lossless_option
        self.remove_option = remove_option
        self.function = function
        self.level_range = level_range

        self.get_input = input_getter
        self.get_output = output_getter

        self.desc_widget = desc_widget
        self.progress_window = progress_window
        self.folder_selection = folder_selection

        self.input_dir = None
        self.output_dir = None

        self.grid_columnconfigure((0, 1), weight=1, uniform="group1")

        if self.lossless_option or self.remove_option or self.level_range:
            self.options_frame = ctk.CTkFrame(self, corner_radius=5)
            self.options_frame.grid(row=0, column=1, padx=0, pady=0, sticky="ew")

        self.button = ctk.CTkButton(
            self,
            text=label,
            command=self.button_callback,
            fg_color="#292929",
            hover_color="#7e3825",
            border_color="#b65033",
            border_width=1,
        )
        self.button.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.button.bind("<Enter>", self.on_button_hover)
        self.button.bind("<Leave>", self.on_button_leave)

        col_index = 0

        if level_range is not None:
            self.quality_slider = ctk.CTkSlider(
                self.options_frame,
                from_=self.level_range[0],
                to=self.level_range[1],
                number_of_steps=self.level_range[1] - self.level_range[0],
                command=self.on_slider_change,
                button_color="#b65033",
                button_hover_color="#7e3825",
                progress_color="#7e3825",
            )
            self.quality_slider.set(self.level_range[2])
            self.quality_slider.grid(
                row=0, column=col_index, padx=5, pady=0, sticky="ew"
            )
            self.quality_slider.grid_columnconfigure(0, weight=1)
            col_index += 1

            self.quality_label = ctk.CTkLabel(
                self.options_frame,
                text=f"{int(self.quality_slider.get())}",
                fg_color="transparent",
            )
            self.quality_label.grid(
                row=0, column=col_index, padx=5, pady=0, sticky="ew"
            )
            col_index += 1

            tip(
                self.quality_slider,
                message=(
                    "Adjust the level for this optimization. Higher "
                    "levels result in better compression but often take longer."
                ),
            )

        if lossless_option is not None:
            self.lossless_check = ctk.CTkCheckBox(
                self.options_frame,
                text="Lossless",
                fg_color="#b65033",
                hover_color="#7e3825",
                checkbox_height=20,
                checkbox_width=20,
                border_width=1,
            )
            lossless_option and self.lossless_check.toggle()
            self.lossless_check.grid(
                row=0, column=col_index, padx=5, pady=0, sticky="ew"
            )
            col_index += 1

            tip(
                self.lossless_check,
                message="Enable 'lossless' compression for this optimization.",
            )

        if remove_option is not None:
            self.remove_check = ctk.CTkCheckBox(
                self.options_frame,
                text="Remove Files",
                fg_color="#b65033",
                hover_color="#7e3825",
                checkbox_height=20,
                checkbox_width=20,
                border_width=1,
            )
            remove_option and self.remove_check.toggle()
            self.remove_check.grid(row=0, column=col_index, padx=5, pady=0, sticky="ew")
            col_index += 1

            tip(
                self.remove_check,
                message=(
                    "Remove the files from the input folder after optimization."
                    "\nLeave disabled to simply copy the remaining files to the output folder."
                ),
            )

    def on_button_hover(self, event):
        self.desc_widget.set_description(self.description)

    def on_button_leave(self, event):
        self.desc_widget.reset_description()

    def on_slider_change(self, event):
        self.quality_label.configure(text=f"{int(self.quality_slider.get())}")

    def button_callback(self):
        input_path_str = self.get_input()
        output_path_str = self.get_output() or input_path_str

        if not input_path_str:
            self.folder_selection.on_empty()
            return

        self.input_dir = Path(input_path_str)
        self.output_dir = Path(output_path_str)

        if not self.input_dir.exists():
            self.folder_selection.on_empty()
            return

        kwargs = {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
        }

        if self.level_range is not None:
            kwargs["level"] = self.quality_slider.get()

        if self.lossless_option is not None:
            kwargs["lossless"] = self.lossless_check.get()

        if self.remove_option is not None:
            kwargs["remove"] = self.remove_check.get()

        kwargs["progress_window"] = self.progress_window

        OptimizationButton.set_state_all_instances("disabled")

        optimization_thread = threading.Thread(
            target=self.function, kwargs=kwargs, daemon=True
        )

        self.progress_window.start(input_dir=self.input_dir, output_dir=self.output_dir)
        optimization_thread.start()
        self.monitor_button_callback_thread(optimization_thread)

    def monitor_button_callback_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_button_callback_thread(thread))
        else:
            self.progress_window.complete()
            OptimizationButton.set_state_all_instances("normal")


class AppInfoFrame(ctk.CTkFrame):
    def __init__(self, root):
        super().__init__(root, corner_radius=0, fg_color="#b65033")

        self.version_number = ctk.CTkLabel(
            self,
            text=f"fOptimizer v{get_project_version()}",
            font=ctk.CTkFont(size=16, family="Calibri", weight="bold"),
        )
        self.version_number.grid(row=0, column=0, padx=(10, 0), pady=0, sticky="nsew")


class App(ctk.CTk):
    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        super().__init__()

        self.title("fOptimizer")
        self.geometry(f"{width}x{height}")
        self.iconbitmap("assets/foptimizer.ico")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.root_scrollable = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.root_scrollable.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.root_scrollable.grid_columnconfigure(0, weight=1)

        self.info_frame = AppInfoFrame(self.root_scrollable)
        self.info_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.input_frame = FolderSelectionFrame(
            self.root_scrollable,
            label="Select Input Folder",
            placeholder_text="",
            tip_text="File path to input folder",
            on_empty_text="Please select an existing input folder",
        )
        self.input_frame.grid(row=1, column=0, padx=0, pady=(3, 0), sticky="nsew")

        self.output_frame = FolderSelectionFrame(
            self.root_scrollable,
            label="Select Output Folder",
            placeholder_text="",
            tip_text=(
                "File path to output folder\nLeave this "
                "field blank to apply changes directly"
                "to the input folder."
            ),
            on_empty_text="",
        )
        self.output_frame.grid(row=2, column=0, padx=0, pady=(0, 10), sticky="nsew")

        # optimization_buttons location

        self.progress_window = ProgressWindow(self.root_scrollable)
        self.progress_window.grid(
            row=99, column=0, padx=10, pady=(20, 0), sticky="ew", columnspan=2
        )

        self.description_label = DescriptionLabel(self.root_scrollable, "")
        self.description_label.grid(
            row=100, column=0, padx=10, pady=(10, 0), sticky="nsew"
        )  # diabolical 100 index row to anchor this to the bottom

        self.optimization_buttons = {}
        for i, (name, info) in enumerate(OPTIMIZATIONS.items()):
            if info["function"] is not None:
                btn = OptimizationButton(
                    self.root_scrollable,
                    label=name,
                    lossless_option=info["lossless_option"],
                    remove_option=info["remove_option"],
                    description=info["description"],
                    function=info["function"],
                    level_range=info.get("level_range", (float, float)),
                    one_click=info["one_click"],
                    input_getter=self.input_frame.get_folder,
                    output_getter=self.output_frame.get_folder,
                    desc_widget=self.description_label,
                    progress_window=self.progress_window,
                    folder_selection=self.input_frame,
                )

                btn.grid(row=i + 3, column=0, padx=10, pady=2.5, sticky="ew")
                self.optimization_buttons[name] = btn


if __name__ == "__main__":
    foptimizer = App()
    foptimizer.mainloop()
