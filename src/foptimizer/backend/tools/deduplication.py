import hashlib
import re
from concurrent.futures import as_completed, ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog

from sourcepp import vpkpp

from .misc import exception_logger, fop_copy


VMT_PARAMS = (
    "$basetexture",
    "$basetexture2",
    "$basetexture3",
    "$basetexture4",
    "$bumpmap",
    "$bumpmap2",
    "$ssbump",
    "$normalmap",
    "$normalmap2",
    "$detail",
    "$detail2",
    "$lightwarptexture",
    "$envmap",
    "$envmapmask",
    "$envmapmask2",
    "$selfillummask",
    "$phongexponenttexture",
    "$phongwarptexture",
    "$phongexponent2texture",
    "$tintmasktexture",
    "$ambientocclusiontexture",
    "$blendmodulatetexture",
    "$tooltexture",
    "$fresnelrangestexture",
    "$emissiveblendtexture",
    "$emissiveblendbasetexture",
    "$emissiveblendflowtexture",
    "$fleshinteriortexture",
    "$fleshinteriornoisetexture",
    "$fleshbordertexture1d",
    "$fleshcubetexture",
    "$fleshnormaltexture",
    "$fleshsubsurfacetexture",
    "$displaceallowance",
    "$parallaxmap",
    "$masks1",
    "$masks2",
    "$maskstexture",
    "$iris",
    "$corneatexture",
    "$fresneltexture",
    "$warptexture",
    "$flowmap",
    "$blendmask",
    "$painttexture",
    "$detailblendmask",
    "$reflecttexture",
    "$refracttexture",
    "$refracttinttexture",
    "$bottommaterial",
    "$underwateroverlay",
    "$backlighttexture",
    "$displacementmap",
    "$ambientoccltexture",
    "$specmasktexture",
    "$fresnelwarptexture",
    "$opacitytexture",
    "$blendmap",
    "$blendmap2",
    "$texture2",
    "%tooltexture",
    "$flow_noise_texture",
    "$paintsplatnormalmap",
    "$paintsplatbubblelayout",
    "$paintsplatbubble",
    "$paintenvmap",
    "$basenormalmap2",
    "$basenormalmap3",
    "$basenormalmap4",
    "$dudvmap",
    "$spitternoisetexture",
    "$scenedepth",
    "$ramptexture",
    "$gradienttexture",
    "$cloudalphatexture",
    "$corecolortexture",
    "$detail1",
    "$detail2",
    "$flowbounds",
    "$masks",
    "$selfillummap",
    "$decaltexture",
    "$lightmap",
    "$compress",
    "$stretch",
    "$texture1",
    "$texture3",
    "$colorbar",
    "$stripetexture",
)

VMT_REGEX = re.compile(
    r"\"?(" + "|".join(re.escape(p) for p in VMT_PARAMS) + r')\"?\s+\"([^"]+)\"',
    re.IGNORECASE,
)


vpk_files = set()


def get_head_directories(
    input_dir: Path,
    target_dir: str,
) -> tuple[Path]:
    """
    Computes a tuple of Paths who are the heads of directories i.e. materials/ folder.

    :param input_dir: The absolute path of the directory to compute the duplicate hashes for.
    :type input_dir: Path
    :param target_dir: The name/delimiter signifying the directory heads.
    :type target_dir: str
    :return: A tuple of Path objects representing the head directories.
    :rtype: tuple
    """
    try:
        found_heads = set()
        target_name = target_dir.lower()

        if input_dir.name.lower() == target_name:
            found_heads.add(input_dir)
            return tuple(found_heads)

        for p in input_dir.rglob("*"):
            if p.is_dir() and p.name.lower() == target_name:
                occurrence_count = sum(1 for part in p.parts if part.lower() == target_name)

                if occurrence_count == 1:
                    found_heads.add(p)

        return tuple(found_heads)

    except Exception as e:
        exception_logger(e)
        return tuple()


def _hash_vtf_worker(vtf_path: Path):
    try:
        vtf_hash = hashlib.md5(vtf_path.read_bytes()).hexdigest()
        return vtf_path, vtf_hash
    except Exception as e:
        return vtf_path, e


def get_duplicate_hash_vtfs(input_dir: Path) -> dict:
    """
    Computes a dictionary of VTF filepaths and their MD5 hashes.

    :param input_dir: The absolute path of the directory to compute the duplicate hashes for.
    :type input_dir: Path
    :return: A dictionary containing a VTF filepath keys and their MD5 hash values.
    :rtype: dict
    """
    try:
        vtf_paths = list(input_dir.rglob("*.vtf"))
        hashes = {}

        with ThreadPoolExecutor() as executor:
            futures = {}
            for path in vtf_paths:
                vtf_hash = executor.submit(_hash_vtf_worker, path)
                futures[vtf_hash] = path

            for future in as_completed(futures):
                try:
                    vtf_path, vtf_hash = future.result()

                    if vtf_hash not in hashes:
                        hashes[vtf_hash] = [vtf_path]
                    else:
                        hashes[vtf_hash].append(vtf_path)

                except Exception as e:
                    print(f"Thread error: {e}")

        duplicates = {}
        for vtf_hash, paths in hashes.items():
            if len(paths) > 1:
                for path in paths:
                    duplicates[path] = vtf_hash

        return duplicates
    except Exception as e:
        exception_logger(e)
        return {}


def get_vmt_dependencies(vmt_dir: Path) -> dict:
    """
    Computes all VMT parameters for each VMT path in the input directory.

    :param input_dir: The absolute path of the directory to compute the duplicate hashes for.
    :type input_dir: Path
    :return: A dictionary containing a VMT filepath keys and their VMT parameter values.
    :rtype: dict
    """

    try:
        vmt_deps = {}
        for vmt_path in vmt_dir.rglob("*.vmt"):
            text = vmt_path.read_text(encoding="latin-1", errors="ignore")
            matches = VMT_REGEX.findall(text)

            for _, path in matches:
                clean_path = path.replace("\\", "/").strip().lower()
                if vmt_path in vmt_deps:
                    vmt_deps[vmt_path].append(clean_path)
                else:
                    vmt_deps[vmt_path] = [clean_path]

        return vmt_deps
    except Exception as e:
        exception_logger(e)
        return {}


def remove_duplicate_vtfs(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
) -> bool:
    """
    Scans for exactly identical duplicate VTF files, moves them to a shared directory,
    removes the original images, and redirects references to old VTFs.

    :param input_dir: The absolute path of the directory to remove the duplicate VTFs from.
    :type input_dir: Path
    :param output_dir: If specified, the absolute path of the
                       directory to copy the duplicate VTFs to.
    :type output_dir: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        if not input_dir.is_dir():
            if progress_window:
                progress_window.error(
                    "Remove Duplicate VTFs failed: "
                    "Input folder was not a folder, or does not exist."
                )
            return False

        materials_roots = get_head_directories(
            input_dir=input_dir, target_dir="materials"
        )
        if not materials_roots:
            if progress_window:
                progress_window.error(
                    "Remove Duplicate VTFs failed: "
                    "No 'materials/' subfolders found in input folder."
                )
            return False

        duplicate_vtfs = get_duplicate_hash_vtfs(input_dir=input_dir)

        if output_dir != input_dir:
            for vtf, _ in duplicate_vtfs.items():
                rel_path = vtf.relative_to(input_dir)
                dst = output_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                fop_copy(src=vtf, dst=dst, mode=2)
            return True

        for materials_root in materials_roots:
            # standardize paths to be relative to materials_root
            duplicate_vtfs_clean = {}
            for path, vtf_hash in duplicate_vtfs.items():
                try:
                    # only process VTFs that actually belong to this materials_root iteration
                    rel_path_clean = (
                        path.relative_to(materials_root)
                        .with_suffix("")
                        .as_posix()
                        .lower()
                    )
                    duplicate_vtfs_clean[rel_path_clean] = vtf_hash
                except ValueError:
                    continue

            shared_dir = materials_root / "foptimizer_shared_duplicates"
            shared_dir.mkdir(parents=True, exist_ok=True)

            for path, vtf_hash in duplicate_vtfs.items():
                if (
                    path.as_posix()
                    .lower()
                    .startswith(materials_root.as_posix().lower())
                ):
                    shared_vtf = shared_dir / f"{vtf_hash}.vtf"
                    if not shared_vtf.exists():
                        fop_copy(src=path, dst=shared_vtf, mode=2)
                    path.unlink()

            # changing vtf references to shared directory
            processed = 0
            vmt_paths = list(materials_root.rglob("*.vmt"))
            total = len(vmt_paths)
            for vmt_path in vmt_paths:
                content = vmt_path.read_text(
                    encoding="latin-1", errors="ignore"
                ).replace("\\", "/")
                modified = False
                matches = VMT_REGEX.findall(content)

                for _, vtf_path in matches:
                    clean_vtf = vtf_path.strip().lower()

                    if clean_vtf in duplicate_vtfs_clean:
                        new_vtf = f"foptimizer_shared_duplicates/{duplicate_vtfs_clean[clean_vtf]}"

                        pattern = re.compile(f'"{re.escape(clean_vtf)}"', re.IGNORECASE)

                        if pattern.search(content):
                            content = pattern.sub(
                                f'"{new_vtf}" // Original: {clean_vtf}',
                                content,
                                count=1,
                            )
                            modified = True

                if modified or "\\" in vmt_path.read_text(
                    encoding="latin-1", errors="ignore"
                ):
                    vmt_path.write_text(content, encoding="latin-1")

                processed += 1
                if progress_window and (processed % 10 == 0 or processed == total):
                    progress_window.update(processed, total)

        return True
    except Exception as e:
        exception_logger(e)
        if progress_window:
            progress_window.error("Remove Duplicate VTFs failed with an unknown error.")
        return False


def _remove_vpk_files_worker(
    f_path: Path,
    input_dir: Path,
    output_dir: Path,
):
    try:
        if not f_path.is_file():
            return None

        rel_path = f_path.relative_to(input_dir)
        match_found = False

        for i in range(len(rel_path.parts)):
            suffix_path = "/".join(rel_path.parts[i:]).lower()
            if suffix_path in vpk_files:
                match_found = True
                break

        if match_found:
            if output_dir != input_dir:
                dst = output_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                fop_copy(src=f_path, dst=dst, mode=1)
            else:
                f_path.unlink()
        return True
    except Exception as e:
        return e


def remove_vpk_files(
    input_dir: Path,
    output_dir: Path,
    vpk_dir: Path = None,
    progress_window=None,
):
    """
    Scans and removes all files with identical relative paths to those in VPK content.

    :param input_dir: The absolute path of the directory to remove duplicate content from.
    :type input_dir: Path
    :param output_dir: If specified, the absolute path of the
                       directory to copy the files already in VPK archives to.
    :type output_dir: Path
    :param vpk_dir: The absolute path of the directory
                    to recursively search for and collect VPK archives from. 
    :type vpk_dir: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """
    try:
        if not input_dir.is_dir():
            if progress_window:
                progress_window.error(
                    "Remove VPK files failed: "
                    "Input folder was not a folder, or does not exist."
                )
            return False

        if not vpk_dir:
            vpk_dir = filedialog.askdirectory(title="Select Game Directory")
            if not vpk_dir:
                if progress_window:
                    progress_window.error(
                        "Remove VPK files failed: No game folder was selected by the user."
                    )
                return False

        vpk_dir = Path(vpk_dir)

        vpk_files.clear()
        for vpk_file in vpk_dir.rglob("*_dir.vpk"):
            vpkpp.VPK.open(
                str(vpk_file),
                lambda path, _: vpk_files.add(path.lower().replace("\\", "/")),
            )

        if not vpk_files:
            if progress_window:
                progress_window.error(
                    "Remove VPK files failed: No VPKs were found in the game directory."
                )
            return False

        all_files = [f for f in input_dir.rglob("*") if f.is_file()]
        total = len(all_files)

        with ThreadPoolExecutor() as executor:
            futures = {}
            for f in all_files:
                future = executor.submit(
                    _remove_vpk_files_worker, f, input_dir, output_dir
                )
                futures[future] = f

            for i, future in enumerate(as_completed(futures), 1):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {futures[future].name}: {e}")

                if progress_window and (i % 10 == 0 or i == total):
                    progress_window.update(i, total)

        return True
    except Exception as e:
        exception_logger(e)
        if progress_window:
            progress_window.error("Remove VPK files failed with an unknown error.")
        return False
