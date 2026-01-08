import shutil
import hashlib
import re
from pathlib import Path

#from .misc import exception_logger


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

VMT_REGEX = re.compile(
    r'\"?(' + '|'.join(re.escape(p) for p in VMT_PARAMS) + r')\"?\s+\"([^"]+)\"', 
    re.IGNORECASE
)


def get_duplicate_hash_vtfs(input_dir: Path) -> dict:
    """
    Computes a dictionary of VTF filepaths and their MD5 hashes.
    
    :param input_dir: The absolute path of the directory to compute the duplicate hashes for.
    :type input_dir: Path
    :return: A dictionary containing a VTF filepath keys and their MD5 hash values.
    :rtype: dict
    """

    hashes = {}
    for vtf_path in input_dir.rglob("*.vtf"):
        hash = hashlib.md5(vtf_path.read_bytes()).hexdigest()
        
        if hash in hashes:
            hashes[hash].append(vtf_path)
        else:
            hashes[hash] = [vtf_path]
            
    duplicates = {}
    for hash, paths in hashes.items():
        if len(paths) > 1:
            for path in paths:
                duplicates[path] = hash
            
    return duplicates
                


def get_vmt_dependencies(vmt_dir: Path) -> dict:
    """
    Computes all VMT parameters for each VMT path in the input directory.
    
    :param input_dir: The absolute path of the directory to compute the duplicate hashes for.
    :type input_dir: Path
    :return: A dictionary containing a VMT filepath keys and their VMT parameter values.
    :rtype: dict
    """
    
    vmt_deps = {}
    for vmt_path in vmt_dir.rglob("*.vmt"):
        text = vmt_path.read_text(encoding="latin-1", errors="ignore")
        matches = VMT_REGEX.findall(text)
        
        for param, path in matches:
            clean_path = path.replace("\\", "/").strip().lower()
            if vmt_path in vmt_deps:
                vmt_deps[vmt_path].append(clean_path) 
            else:
                vmt_deps[vmt_path] = [clean_path]
    
    return vmt_deps


def remove_duplicate_vtfs(input_dir: Path, output_dir: Path, progress_window=None) -> bool:
    """
    Scans for exactly identical duplicate VTF files, moves them to a shared directory, removes the original images, and redirects references to old VTFs.
    """

    if not input_dir.is_dir():
        if progress_window:
            progress_window.update(1, 1)
        return False
    
    duplicate_vtfs = get_duplicate_hash_vtfs(input_dir=input_dir)
    if output_dir != input_dir:
        for vtf in duplicate_vtfs.keys():
            rel_path = vtf.relative_to(input_dir)
            dst = output_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            try: shutil.copy2(vtf, dst)
            except: pass
        return True
    
    if input_dir.name == "materials":
        materials_root = input_dir
    else:
        materials_root = input_dir / "materials"
        
    if not materials_root.is_dir():
        print("No materials directory found.")
        return False

    # standardize paths to be relative to materials_root
    duplicate_vtfs_clean = {}
    for path, hash in duplicate_vtfs.items():
        rel_path_clean = path.relative_to(materials_root).with_suffix("").as_posix().lower()
        duplicate_vtfs_clean[rel_path_clean] = hash

    shared_dir = materials_root / "foptimizer_shared_duplicates"
    shared_dir.mkdir(parents=True, exist_ok=True)
    
    for path, hash in duplicate_vtfs.items():
        shared_vtf = shared_dir / f"{hash}.vtf"
        if not shared_vtf.exists():
            try: shutil.copy2(path, shared_vtf)
            except: pass
        path.unlink()

    # changing vtf references to shared directory
    processed = 0
    vmt_paths = list(input_dir.rglob("*.vmt"))
    total = len(vmt_paths)
    for vmt_path in vmt_paths:
        content = vmt_path.read_text(encoding="latin-1", errors="ignore").replace("\\", "/")
        modified = False
        matches = VMT_REGEX.findall(content)
        
        for param, vtf_path in matches:
            clean_vtf = vtf_path.strip().lower()
            
            if clean_vtf in duplicate_vtfs_clean:
                new_vtf = f"foptimizer_shared_duplicates/{duplicate_vtfs_clean[clean_vtf]}"
                
                pattern = re.compile(f'"{re.escape(clean_vtf)}"', re.IGNORECASE)
                
                if pattern.search(content):
                    content = pattern.sub(f'"{new_vtf}" // Original: {clean_vtf}', content, count=1)
                    modified = True
        
        if modified or "\\" in vmt_path.read_text(encoding="latin-1", errors="ignore"):
            vmt_path.write_text(content, encoding='latin-1')
            
        processed += 1
        if progress_window:
            progress_window.update(processed, total)

    return True