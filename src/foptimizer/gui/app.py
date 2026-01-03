import threading
from tkinter import filedialog
from pathlib import Path

import customtkinter as ctk
from CTkToolTip import CTkToolTip as tip

import foptimizer.backend.logic as backend
from foptimizer.backend.tools.misc import get_project_version


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("assets/foptimizer-theme.json")

DEFAULT_WIDTH = 760
DEFAULT_HEIGHT = 540

OPTIMIZATIONS = {
    "Fit Alpha": {
        "description": "Strip unnecessary channels from VTF images, 'fitting' their formats as exactly as possible.", 
        "lossless_option": True,
        "quality_range" : (None, None),
        "remove_option" : False,
        "function" : backend.logic_fit_alpha,
    },
    "Remove Redundant Files": {
        "description": "Removes files unused by both modern engine branches and modding tools.", 
        "lossless_option": False,
        "quality_range" : (None, None),
        "remove_option" : True,
        "function": backend.logic_remove_unused_files,
    },
    "Shrink Solid Colour Images": {
        "description": "Shrinks all solid-colour VTFs to a minimum resolution, keeping its usage identical but filesize minimal.", 
        "lossless_option": False,
        "quality_range" : (None, None),
        "remove_option" : False,
        "function": backend.logic_shrink_solid,
    },
    "PNG Optimization": {
        "description": "Optimizes a folder of PNG images losslessly using oxipng.", 
        "lossless_option": True,
        "quality_range" : (0, 6),
        "remove_option" : False,
        "function": backend.logic_optimize_png,
    },
    "Halve Normals": {
        "description": "Halves the dimensions of all normal map VTF images: also encodes a flag to prevent halving the same image twice.", 
        "lossless_option": False,
        "quality_range" : (None, None),
        "remove_option" : False,
        "function": backend.logic_halve_normals,
    },
    "WAV to OGG": {
        "description": "Converts all WAV files to OGG files, trading slight quality loss for a large filesize reduction.\n\
WARNING: you have to change all references to .wav files to .ogg in code and on maps!", 
        "lossless_option": False,
        "quality_range" : (-1, 10),
        "remove_option" : True,
        "function": backend.logic_wav_to_ogg,
    },
    "Remove Unaccessed VTFs": {
        "description": "Removes all VTF files not referenced by any VMT in the input folder.\n\
WARNING: this will remove VTF images referenced only in code!",
        "lossless_option": False,
        "quality_range" : (None, None),
        "remove_option" : True,
        "function": backend.logic_remove_unaccessed_vtfs,
    },
}


class FolderSelectionFrame(ctk.CTkFrame):
    def __init__(self, root, label: str, placeholder_text: str):
        super().__init__(root)

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=label)
        self.label.grid(row=0, column=0, columnspan=2, padx=10, pady=(3, 0), sticky="w")

        self.field = ctk.CTkEntry(self, placeholder_text=placeholder_text)
        self.field.grid(row=1, column=0, padx=(10, 5), pady=(5, 10), sticky="ew")
        
        self.browse_button = ctk.CTkButton(self, text="Browse", width=100, command=self.browse, fg_color="#b65033", hover_color="#7e3825")
        self.browse_button.grid(row=1, column=1, padx=(5, 10), pady=(5, 10))
    
    def browse(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            self.field.delete(0, "end")
            self.field.insert(0, folder)
    
    def get_folder(self):
        path_text = self.field.get().strip()
        return path_text if path_text != "" else None


class DescriptionLabel(ctk.CTkLabel):
    def __init__(self, root, default_text: str):
        super().__init__(root, text=default_text, justify="left")
        self.default_text = default_text
        self.configure(wraplength=DEFAULT_WIDTH)

    def set_description(self, text: str):
        self.configure(text=text)

    def reset_description(self):
        self.configure(text=self.default_text)


class ProgressBar(ctk.CTkProgressBar):
    def __init__(self, root, mode="determinate", corner_radius=5, progress_color="#b65033"):
        super().__init__(root)

        self.configure(mode=mode, corner_radius=corner_radius, progress_color=progress_color)
        self.grid(row=99, column=0, padx=10, pady=(10, 10), sticky="ew", columnspan=2)
        self.set(0)


class OptimizationButton(ctk.CTkFrame):
    def __init__(self, root, label, description, lossless_option, remove_option, function,
                 input_getter, output_getter, desc_widget: DescriptionLabel, progress_bar: ProgressBar, quality_range=(float, float)):
        super().__init__(root)

        self.label = label
        self.description = description
        self.lossless_option = lossless_option
        self.remove_option = remove_option
        self.function = function
        self.range = quality_range

        self.get_input = input_getter
        self.get_output = output_getter

        self.desc_widget = desc_widget
        self.progress_bar = progress_bar
        
        self.grid_columnconfigure((0, 1), weight=1, uniform="group1")

        self.options_frame = ctk.CTkFrame(self, corner_radius=5)
        self.options_frame.grid(row=0, column=1, padx=0, pady=0, sticky="ew")

        self.button = ctk.CTkButton(self, text=label, command=self.button_callback, fg_color="#b65033", hover_color="#7e3825")
        self.button.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.button.bind("<Enter>", self.on_button_hover)
        self.button.bind("<Leave>", self.on_button_leave)

        col_index = 0

        if self.range != (None, None):
            self.quality_slider = ctk.CTkSlider(self.options_frame, from_=self.range[0], to=self.range[1],
                                                number_of_steps=self.range[1] - self.range[0], command = self.on_slider_change,
                                                button_color="#b65033", button_hover_color="#7e3825", progress_color="#7e3825", border_width=1)
            self.quality_slider.set(self.range[1])
            self.quality_slider.grid(row=0, column=col_index, padx=5, pady=0, sticky="ew")
            self.quality_slider.grid_columnconfigure(0, weight=1)
            col_index+=1

            self.quality_label = ctk.CTkLabel(self.options_frame, text=f"{self.quality_slider.get()}", fg_color="transparent")
            self.quality_label.grid(row=0, column=col_index, padx=5, pady=0, sticky="ew")
            col_index+=1

            tip(self.quality_slider, message="Adjust the level for this optimization. Higher levels result in better compression but often take longer.")
            
        if lossless_option:
            self.lossless_check = ctk.CTkCheckBox(self.options_frame, text="Lossless", fg_color="#b65033",
                                                  hover_color="#7e3825", checkbox_height=20, checkbox_width=20, border_width=1)
            self.lossless_check.grid(row=0, column=col_index, padx=5, pady=0, sticky="ew")
            col_index+=1

            tip(self.lossless_check, message="Enable 'lossless' compression for this optimization.")

        if remove_option:
            self.remove_check = ctk.CTkCheckBox(self.options_frame, text="Remove Files", fg_color="#b65033",
                                                hover_color="#7e3825", checkbox_height=20, checkbox_width=20, border_width=1)
            self.remove_check.grid(row=0, column=col_index, padx=5, pady=0, sticky="ew")
            col_index+=1

            tip(self.remove_check, message="Remove the files from the input folder after optimization.")

        if col_index == 0:
            self.options_frame.destroy()

    def on_button_hover(self, event):
        self.desc_widget.set_description(self.description)

    def on_button_leave(self, event):
        self.desc_widget.reset_description()

    def on_slider_change(self, event):
        self.quality_label.configure(text=f"{self.quality_slider.get()}")

    def button_callback(self):
        input_path = self.get_input()
        output_path = self.get_output() or input_path

        if not input_path:
            return
        
        kwargs = {
            "input_dir": Path(input_path),
            "output_dir": Path(output_path),
        }

        if self.range != (None, None):
            kwargs["level"] = self.quality_slider.get()
                
        if self.lossless_option:
            kwargs["lossless"] = self.lossless_check.get()
            
        if self.remove_option:
            kwargs["remove"] = self.remove_check.get()

        kwargs["progress_bar"] = self.progress_bar

        self.button.configure(state="disabled")

        optimization_thread = threading.Thread(
                target=self.function, 
                kwargs=kwargs, 
                daemon=True
                )
        optimization_thread.start()
        self.monitor_thread(optimization_thread)

    def monitor_thread(self, thread):
            if thread.is_alive():
                self.after(100, lambda: self.monitor_thread(thread))
            else:
                self.button.configure(state="normal")


class AppInfoFrame(ctk.CTkFrame):
    def __init__(self, root):
        super().__init__(root, corner_radius=0, fg_color="#b65033")

        self.version_number = ctk.CTkLabel(self, text=f"fOptimizer v{get_project_version()}", font=ctk.CTkFont(size=16, family="Calibri", weight="bold"))
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

        self.input_frame = FolderSelectionFrame(self.root_scrollable, "Select Input Folder",
                                                "Absolute path to input folder")
        self.input_frame.grid(row=1, column=0, padx=0, pady=(3, 0), sticky="nsew")

        self.output_frame = FolderSelectionFrame(self.root_scrollable, "Select Output Folder", 
                                                "Absolute path to output folder (leave this field blank to apply changes directly to the input folder)")
        self.output_frame.grid(row=2, column=0, padx=0, pady=0, sticky="nsew")

        # optimization_buttons location

        self.description_label = DescriptionLabel(self.root_scrollable, "")
        self.description_label.grid(row=100, column=0, padx=10, pady=0, sticky="nsew") # diabolical 100 index row to anchor this to the bottom

        self.progress_bar = ProgressBar(self.root_scrollable)

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
                    quality_range=info.get("quality_range", (float, float)),
                    input_getter=self.input_frame.get_folder,
                    output_getter=self.output_frame.get_folder,
                    desc_widget=self.description_label,
                    progress_bar=self.progress_bar
                )
            
                btn.grid(row=i + 3, column=0, padx=10, pady=2.5, sticky="ew")
                self.optimization_buttons[name] = btn

if __name__ == "__main__":
    foptimizer = App()
    foptimizer.mainloop()