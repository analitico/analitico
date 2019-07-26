import tempfile
import pandas as pd
from pathlib import Path

from api.libcloud.webdavdrivers import WebdavStorageDriver, METADATA_EXTRA_TAG

from analitico import logger

import analitico.pandas
import analitico.schema
import analitico.utilities

import api.libcloud.iterio


import libcloud.storage.base


def get_file_metadata(driver: WebdavStorageDriver, path: str, refresh: bool = True) -> libcloud.storage.base.Object:
    """ Retrieve file object from path. """
    ls = driver.ls(path)
    assert len(ls) == 1
    obj = ls[0]

    if refresh:
        if not (obj and obj.meta_data and obj.meta_data.get("metadata_hash") == obj.hash):
            obj = refresh_file_metadata(driver, path, obj)

    return obj


def refresh_file_metadata(driver: WebdavStorageDriver, path: str, obj: libcloud.storage.base.Object):
    metadata = {"metadata_hash": obj.hash}

    df = None

    # file suffix, eg: .csv, .pdf
    suffix = Path(path).suffix.lower()
    if suffix in (".csv",):
        try:
            asset_io = api.libcloud.iterio.IterIO(driver.download_as_stream(path))
            df = analitico.pandas.pd_read_csv(asset_io)
        except Exception as exc:
            logger.warning("refresh_file_metadata - could not read csv file: %s", path)
            raise exc
    if suffix in (".parquet",):
        try:
            asset_io = api.libcloud.iterio.IterIO(driver.download_as_stream(path))
            df = pd.read_parquet(asset_io)
        except Exception as exc:
            logger.warning("refresh_file_metadata - could not read parquet file: %s", path)
            raise exc

    if df is not None:
        metadata["total_records"] = len(df.index)
        metadata["schema"] = analitico.schema.generate_schema(df)

    # update metadata on storage
    driver.set_metadata(path, metadata=metadata)
    return driver.ls(path)[0]
