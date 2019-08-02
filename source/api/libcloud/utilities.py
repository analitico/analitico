import tempfile
import libcloud.storage.base

from pathlib import Path
from analitico import logger


def clone_files(item, clone, item_path=None, item_driver=None, clone_driver=None):
    """
    Recursively clone storage files and directories in item to clone.
    
    Arguments:
        item {Dataset, Recipe, Notebook} -- Item we copy files from.
        clone {Dataset, Recipe, Notebook} -- Item we copy files to.
    """
    try:
        if not item_driver:
            item_driver = item.storage.driver
        if not clone_driver:
            clone_driver = clone.storage.driver
        if not item_path:
            item_path = item.storage_base_path

        # current directory exists?
        clone_path_checked = False

        if item_driver.exists(item_path):
            ls = item_driver.ls(item_path)
            # check all except / which is base directory path
            for item_file in ls[1:]:
                clone_path = item_file.name.replace(item.storage_base_path, clone.storage_base_path)
                if isinstance(item_file, libcloud.storage.base.Container):
                    # clone entire directory recursively
                    clone_driver.mkdirs(clone_path)
                    clone_files(item, clone, item_file.name, item_driver, clone_driver)
                    clone_path_checked = True
                else:
                    # check if the directory containing the file actually does exist, if not make it
                    if not clone_path_checked:
                        clone_dir = clone_path[: clone_path.rfind("/") + 1]
                        clone_driver.mkdirs(clone_dir)
                        clone_path_checked = True
                    suffix = Path(item_file.name).suffix
                    # clone single file by downloading + uploading
                    with tempfile.NamedTemporaryFile(prefix="clone_", suffix=suffix) as f:
                        item_driver.download(item_file.name, f.name)
                        clone_driver.upload(f.name, clone_path)

    except Exception as exc:
        logger.error(f"clone_files - item: {item.id}, clone: {clone.id}, base_path: {item_path}, exc: {exc}")
        raise exc
