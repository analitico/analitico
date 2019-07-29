import tempfile
import diskcache
import pandas as pd
import os
import libcloud.storage

from pathlib import Path
from rest_framework import status

import analitico.pandas
import analitico.schema
import analitico.utilities
from analitico import AnaliticoException, logger, PARQUET_SUFFIXES, CSV_SUFFIXES, EXCEL_SUFFIXES, HDF_SUFFIXES
from analitico.pandas import pd_read_csv

import api.libcloud.iterio
from api.libcloud.webdavdrivers import WebdavStorageDriver

# Diskcache is used to cache file's metadata on the server
# http://www.grantjenks.com/docs/diskcache/tutorial.html
# http://www.grantjenks.com/docs/diskcache/api.html
# Pros:
#   Simple: servers don't need to coordinate
#   Fast: data is stored on local disk
# Cons:
#   Data is lost when server is restarted
#   Data needs to be recalculated on each server


# how long we store metadata for? 1 month
_cache_expire = 60 * 60 * 24 * 31

# temporary directory where items are stored
_cache_directory = os.path.join(tempfile.gettempdir(), "analitico-metadata-cache")
if not os.path.isdir(_cache_directory):
    os.makedirs(_cache_directory)

# cache object is global so it stays open
_cache = diskcache.Cache(_cache_directory)


##
## Public methods
##


def get_file_metadata(driver: WebdavStorageDriver, path: str, refresh: bool = True) -> dict:
    """
    Retrieve file object from path.
    
    Arguments:
        driver {WebdavStorageDriver} -- Storage driver used to retrieve the file
        path {str} -- The path of the asset on disk
    
    Keyword Arguments:
        refresh {bool} -- True if metadata should be refreshed if stale or missing (default: {True})
    
    Returns:
        dict -- The object's metadata (if any).
    """
    ls = driver.ls(path)

    if len(ls) == 1 and isinstance(ls[0], libcloud.storage.base.Object):
        obj = ls[0]
    else:
        # no metadata for directories for now
        return {}

    # retrieve metadata from disk cache if availa
    metadata_key = f"{driver.url}{path}#{obj.hash}"
    metadata = _cache.get(metadata_key)

    # should create missing metadata?
    if metadata is None and refresh:
        metadata = {}

        # file suffix, eg: .csv, .pdf
        suffix = Path(path).suffix.lower()

        # can this file be read into a pandas dataframe?
        if suffix in analitico.PANDAS_SUFFIXES:
            df = get_file_dataframe(driver, path)
            if df is not None:
                metadata["total_records"] = len(df.index)
                metadata["schema"] = analitico.schema.generate_schema(df)
                metadata["describe"] = df.describe().to_dict()

        try:
            # store updated metadata in local disk cache
            _cache.set(metadata_key, metadata, expire=_cache_expire)
        except Exception as exc:
            logger.warning("get_file_metadata - could not save metadata for %s, exc: %s", metadata_key, exc)

    return metadata


def get_file_dataframe(
    driver: WebdavStorageDriver, path: str, page: int = 0, page_size: int = None, query: str = None, sort: str = None
) -> pd.DataFrame:
    """
    Returns the tabular data file asset at the given path loaded into a Pandas
    data frame. Optionally this method will apply paging and filtering to the
    dataset and return only the filtered rows. The file must be one of the
    supported formats, see: analitico.PANDAS_SUFFIXES

    Arguments:
        driver {WebdavStorageDriver} -- Storage driver used to retrieve the file
        path {str} -- The path of the asset on disk

    Keyword Arguments:
        page {int} -- Page number, if paged (default: {0})
        page_size {int} -- Page size, use None to get whole dataset (default: {None})
        query {str} -- Query string to be applied to filter records (default: {None})
        sort {str} -- Comma separated list of columns for sorting, use - for descending (default: {None})

    Returns:
        pd.DataFrame -- Records as a Pandas dataframe.
    """

    obj_stream = driver.download_as_stream(path)
    obj_io = api.libcloud.iterio.IterIO(obj_stream)

    # true if dataframe has already been paged
    already_paged = False

    suffix = Path(path).suffix
    if suffix in CSV_SUFFIXES:
        if not query and page_size:
            # read csv from stream, skip offset rows, read only rows we care about
            df = pd_read_csv(obj_io, skiprows=range(1, (page * page_size) + 1), nrows=page_size)
            already_paged = True
        else:
            df = pd_read_csv(obj_io)
    elif suffix in PARQUET_SUFFIXES:
        df = pd.read_parquet(obj_io)
    elif suffix in EXCEL_SUFFIXES:
        # reading stream is not supported yet
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            driver.download(path, f.name)
            df = pd.read_excel(f.name)
    elif suffix in HDF_SUFFIXES:
        # reading stream is not supported yet
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            driver.download(path, f.name)
            df = pd.read_hdf(f.name, "df")
    else:
        raise AnaliticoException(f"Unknown format for {path}.", status_code=status.HTTP_400_BAD_REQUEST)

    if query:
        try:
            # examples:
            # https://www.geeksforgeeks.org/python-filtering-data-with-pandas-query-method/
            df.query(query, inplace=True)
        except Exception as exc:
            raise AnaliticoException(
                f"Query could not be completed: {exc}",
                status_code=status.HTTP_400_BAD_REQUEST,
                extra={"query": query, "error": str(exc)},
            ) from exc

    if sort:
        # eg: ?sort=Name,-Age
        columns = sort.split(",")
        for column in columns:
            if column.startswith("-"):
                df.sort_values(column[1:], ascending=False, inplace=True)
            else:
                df.sort_values(column, inplace=True)

    if not already_paged and page_size:
        page_offset = page * page_size
        df = df.iloc[page_offset : page_offset + page_size]

    return df


def apply_conversions(driver: WebdavStorageDriver, path: str, new_path: str = None, new_schema: dict = None):
    """
    Converts data files from a format to another or applies a new schema to transform columns, etc.
    
    Arguments:
        driver {WebdavStorageDriver} -- Storage driver used to retrieve the file
        path {str} -- The path of the asset on disk
    
    Keyword Arguments:
        new_path {str} -- The new path (with new suffix) (default: {None})
        new_schema {dict} -- The new schema to be applied (default: {None})
    """

    # read dataframe in its entirety, no paging
    df = get_file_dataframe(driver, path)

    # do we apply a new schema?
    if new_schema:
        df = analitico.schema.apply_schema(df, new_schema)

    # what format do we write to?
    new_suffix = Path(new_path if new_path else path).suffix.lower()

    # write dataframe to a temp file then upload to storage path
    with tempfile.NamedTemporaryFile(mode="w+", prefix="df_", suffix=new_suffix) as f:
        if new_suffix in CSV_SUFFIXES:
            df.to_csv(f.name)
        elif new_suffix in PARQUET_SUFFIXES:
            df.to_parquet(f.name)
        elif new_suffix in EXCEL_SUFFIXES:
            # writer = pd.ExcelWriter(f.name, engine='xlsxwriter', date_format='YYYY-MM-DD', datetime_format='YYYY-MM-DD HH:MM:SS')
            writer = pd.ExcelWriter(f.name, date_format="YYYY-MM-DD", datetime_format="YYYY-MM-DD HH:MM:SS")
            df.to_excel(writer, index=False)
        elif new_suffix in HDF_SUFFIXES:
            df.to_hdf(f.name, key="df", mode="w")
        else:
            raise AnaliticoException(f"Unknown format for {path}.", status_code=status.HTTP_400_BAD_REQUEST)

        driver.upload(f.name, new_path if new_path else path)

        # file has moved to new location?
        if new_path and path != new_path:
            driver.delete(path)

    return True
