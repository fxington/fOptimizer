import shutil
from pathlib import Path

from .misc import exception_logger, fop_copy
from .patcher import get_head_directories, get_vmt_dependencies


FILE_BLACKLIST = (
    "*.360.vtx",
    "*.dx80.vtx",
    "*.sw.vtx",
    "*.xbox.vtx",
)


def remove_unused_files(
    input_dir: Path, output_dir: Path, remove: bool, progress_window=None
) -> bool:
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
        if progress_window:
            progress_window.update(0, 0)

        if not input_dir.is_dir():
            if progress_window:
                progress_window.error(
                    "Remove Unused Files failed: Input folder was not a folder, or does not exist."
                )
            return False

        if remove:
            del_dir = input_dir
        else:
            shutil.copytree(src=input_dir, dst=output_dir)
            del_dir = output_dir

        total = sum(1 for entry in del_dir.rglob("*") if entry.is_file())

        for blacklisted_type in FILE_BLACKLIST:
            f_list = del_dir.rglob(blacklisted_type)

            processed = 0
            for f in f_list:
                f.unlink()

                processed += 1
                if progress_window:
                    progress_window.update(processed, total)

        return True
    except Exception as e:
        exception_logger(e)
        if progress_window:
            progress_window.error("Remove Unused Files failed with an unknown error.")
        return False


def remove_unaccessed_vtfs(
    input_dir: Path, output_dir: Path, remove: bool = False, progress_window=None
) -> bool:
    """
    Scans for VTF files not referenced by any VMT in the directory tree.

    :param input_dir: The directory to remove unaccessed VTFs from.
    :type input_dir: Path
    :param output_dir: The directory to copy over only used files to.
    :type output_dir: Path
    :param remove: True if the function should remove unused from the input directory instead
        of copying non-blacklisted to the output directory.
    :return: Whether the function completed successfully.
    :rtype: bool
    """
    try:
        if not input_dir.is_dir():
            if progress_window:
                progress_window.error(
                    "Remove Unaccessed VTFs failed: "
                    "Input folder was not a folder, or does not exist."
                )
            return False

        materials_roots = get_head_directories(
            input_dir=input_dir, target_dir="materials"
        )
        if not materials_roots:
            if progress_window:
                progress_window.error(
                    "Remove Unaccessed VTFs failed: No 'materials/' subfolders found."
                )
            return False

        all_deps_map = get_vmt_dependencies(input_dir)
        vmt_deps = set()
        for deps in all_deps_map.values():
            for vtf_path in deps:
                clean_vtf = vtf_path.lower().replace("\\", "/")
                if not clean_vtf.endswith(".vtf"):
                    clean_vtf += ".vtf"

                vmt_deps.add(clean_vtf)
                if clean_vtf.startswith("materials/"):
                    vmt_deps.add(clean_vtf.replace("materials/", "", 1))

        for materials_root in materials_roots:
            vmt_files = list(materials_root.rglob("*.vmt"))
            vtf_files = list(materials_root.rglob("*.vtf"))

            total = len(vmt_files) + len(vtf_files)
            if not remove:
                total += len(vmt_files)

            processed = len(vmt_files)
            for vtf_path in vtf_files:
                rel_path = vtf_path.relative_to(materials_root).as_posix().lower()

                is_used = rel_path in vmt_deps

                if not is_used:
                    if remove:
                        vtf_path.unlink()
                else:
                    if not remove:
                        target_path = output_dir / vtf_path.relative_to(input_dir)
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        fop_copy(src=vtf_path, dst=target_path, mode=2)

                processed += 1
                if progress_window:
                    progress_window.update(processed, total)

            if not remove:
                for vmt_path in vmt_files:
                    target_path = output_dir / vmt_path.relative_to(input_dir)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    fop_copy(src=vmt_path, dst=target_path, mode=2)

                    processed += 1
                    if progress_window:
                        progress_window.update(processed, total)

        return True
    except Exception as e:
        exception_logger(e)
        if progress_window:
            progress_window.error(
                "Remove Unaccessed VTFs failed with an unknown error."
            )
        return False
