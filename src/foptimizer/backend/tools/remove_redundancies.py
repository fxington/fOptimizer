import shutil
from pathlib import Path

from .misc import exception_logger

VMT_PARAMS = (
    "$basetexture", "$basetexture2", "$basetexture3", "$bumpmap", 
    "$bumpmap2", "$ssbump", "$normalmap", "$normalmap2", "$detail", 
    "$detail2", "$lightwarptexture", "$envmap", "$envmapmask", 
    "$envmapmask2", "$selfillummask", "$phongexponenttexture", 
    "$phongwarptexture", "$phongexponent2texture", "$tintmasktexture", 
    "$ambientocclusiontexture", "$blendmodulatetexture", "$tooltexture", 
    "$fresnelrangestexture", "$emissiveblendtexture", 
    "$emissiveblendbasetexture", "$emissiveblendflowcustomtexture", 
    "$fleshinteriortexture", "$fleshinteriornoisetexture", 
    "$fleshbordertexture1d", "$fleshcubetexture", "$fleshnormaltexture", 
    "$fleshsubsurfacetexture", "$displaceallowance", "$parallaxmap", 
    "$masks1", "$masks2", "$maskstexture", "$iris", "$corneatexture",
    "$fresneltexture", "$warptexture", "$flowmap", "$blendmask",
    "$painttexture", "$detailblendmask", "$reflecttexture",
    "$refracttexture", "$refracttinttexture", "$bottommaterial",
    "$underwateroverlay", "$backlighttexture", "$displacementmap",
)

FILE_BLACKLIST = (
    ".360.vtx",
    ".dx80.vtx",
    ".sw.vtx",
    ".xbox.vtx",
)

def remove_unused_files(input_dir: Path, output_dir: Path, remove: bool, progress_window=None) -> bool:
    """
    Copies used files to output_dir while skipping unused legacy formats.
    
    :param input_dir: The directory to isolate unused file formats from.
    :type input_dir: Path
    :param output_dir: The directory to copy over only used file formats to.
    :type output_dir: Path    
    :param remove: True if the function should remove unused from the input directory instead
        of copying non-blacklisted to the output directory.
    :type remove: bool
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        if not input_dir.is_dir():
            if progress_window:
                progress_window.update(1, 1)
            return True

        files = [f for f in input_dir.rglob("*") if f.is_file()]
        total = len(files)
        processed = 0

        for file_path in files:
            if any(file_path.name.lower().endswith(ext) for ext in FILE_BLACKLIST):
                if remove:
                    file_path.unlink()
            else:
                if not remove:
                    relative_path = file_path.relative_to(input_dir)
                    target_path = output_dir / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    try: shutil.copy(file_path, target_path)
                    except: pass
            
            processed += 1
            if progress_window:
                progress_window.update(processed, total)
        
        return True
    except Exception as e:
        exception_logger(e)
        return False


def remove_unaccessed_vtfs(input_dir: Path, output_dir: Path, remove: bool = False, progress_window=None) -> bool:
    """
    Scans for VTF files not referenced by any VMT in the directory tree.
    
    :param input_dir: The directory to remove unaccessed VTFs from.
    :param remove: True if the function should remove unused from the input directory instead
        of copying non-blacklisted to the output directory.
    :return: Whether the function completed successfully.
    :rtype: bool
    """
    try:
        if not input_dir.is_dir():
            if progress_window:
                progress_window.update(1, 1)
            return True

        vmt_deps = set()
        vmt_files = list(input_dir.rglob("*.vmt"))
        vtf_files = list(input_dir.rglob("*.vtf"))
        
        total = len(vmt_files) + len(vtf_files)
        if not remove:
            total += len(vmt_files)
        
        processed = 0

        for vmt_path in vmt_files:
            with vmt_path.open('r', errors='ignore') as f:
                for line in f:
                    line = line.strip().lower()
                    if any(param.lower() in line for param in VMT_PARAMS):
                        parts = line.split()
                        if len(parts) >= 2:
                            tex = parts[1].strip('"').replace("\\", "/").strip()
                            if not tex.endswith('.vtf'):
                                tex += '.vtf'
                            vmt_deps.add(tex)
            processed += 1
            if progress_window:
                progress_window.update(processed, total)

        for vtf_path in vtf_files:
            rel_path = vtf_path.relative_to(input_dir).as_posix().lower()
            rel_path_no_mats = rel_path.replace("materials/", "", 1) if rel_path.startswith("materials/") else rel_path
            
            is_used = (rel_path in vmt_deps or rel_path_no_mats in vmt_deps)

            if not is_used:
                if remove:
                    vtf_path.unlink()
            else:
                if not remove:
                    target_path = output_dir / vtf_path.relative_to(input_dir)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    try: shutil.copy(vtf_path, target_path)
                    except: pass
            
            processed += 1
            if progress_window:
                progress_window.update(processed, total)

        if not remove:
            for vmt_path in vmt_files:
                target_path = output_dir / vmt_path.relative_to(input_dir)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                try: shutil.copy(vmt_path, target_path)
                except: pass
                processed += 1
                if progress_window:
                    progress_window.update(processed / total)

        return True
    except Exception as e:
        exception_logger(e)
        return False