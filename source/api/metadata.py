import tempfile
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
from api.k8 import k8_job_generate_dataset_metadata, kubectl, K8_DEFAULT_NAMESPACE
from api.models import ItemMixin

import api.libcloud.iterio
from api.libcloud.webdavdrivers import WebdavStorageDriver

# use simplejson instead of standard built in library
# mostly because it has a parameter which supports replacing nan with nulls
# thus producing json which is ecma compliant and won't have issues being read
# https://simplejson.readthedocs.io/en/latest/
import simplejson as json

# dataframe size limit for exploring, quering and generating metadata
DATAFRAME_OPEN_SIZE_LIMIT_MB = 100


##
## Public methods
##


def get_metadata_path(path: str):
    """ 
    Return the path where the file metadata is saved.
    Eg: datasets/ds_titanic/.analitico/titanic.csv.json
    """
    return os.path.join(os.path.dirname(path), ".analitico/", os.path.basename(path) + ".json")


def get_file_metadata(item: ItemMixin, driver: WebdavStorageDriver, path: str, refresh: bool = True) -> dict:
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

    # file suffix, eg: .csv, .pdf
    suffix = Path(path).suffix.lower()

    # can this file be read into a pandas dataframe?
    if suffix not in analitico.PANDAS_SUFFIXES:
        return {}

    # retrieve metadata from disk if available
    try:
        # eg: datasets/ds_titanic/.analitico/titanic.csv.metadata
        metadata_path = get_metadata_path(path)
        content = next(iter(driver.download_as_stream(metadata_path)))
        metadata = json.loads(content)
        if metadata.get("hash") != obj.hash:
            # it needs to be refreshed because file has changed
            metadata = {}
    except Exception as e:
        logger.debug(f"metadata for the file {path} does not exist")
        metadata = {}

    try:
        # should create missing metadata?
        if not metadata and refresh:
            metadata = {}

            # generate metadata asyncronous due to memory limits
            # to open the dataset with Pandas.
            # First check the job is not already running.
            jobs, _ = kubectl(
                K8_DEFAULT_NAMESPACE,
                "get",
                "job",
                args=[
                    "--selector",
                    f"analitico.ai/job-action={analitico.ACTION_DATASET_METADATA},analitico.ai/item-id={item.id},analitico.ai/dataset-hash={obj.hash}",
                ],
            )
            if len(jobs["items"]) == 0:
                k8_job_generate_dataset_metadata(item, path, obj.hash, extra=obj.extra)

    except Exception as exc:
        logger.warning("get_file_metadata - could not save metadata for %s, exc: %s", path, exc)
        metadata = {}

    return metadata


def get_file_dataframe(
    driver: WebdavStorageDriver, path: str, page: int = 0, page_size: int = None, query: str = None, sort: str = None
) -> (pd.DataFrame, int):
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
        int -- Number of rows in dataframe (if known).
    """
    # skip metadata for big files otherwise request can stuck
    ls = driver.ls(path)
    if len(ls) == 1 and isinstance(ls[0], libcloud.storage.base.Object):
        obj = ls[0]
        if obj.size > analitico.utilities.size_to_bytes(f"{DATAFRAME_OPEN_SIZE_LIMIT_MB}MB"):
            raise AnaliticoException(
                f"Dataframe is too large to be opened (limit set to {DATAFRAME_OPEN_SIZE_LIMIT_MB}MB)",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

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
        by = []
        ascending = []
        for column in columns:
            if column.startswith("-"):
                by.append(column[1:])
                ascending.append(False)
            else:
                by.append(column)
                ascending.append(True)

        df.sort_values(by, ascending=ascending, inplace=True)

    # number of total rows is unknown if we're prepaging the file
    rows = None if already_paged else len(df.index)

    if not already_paged and page_size:
        page_offset = page * page_size
        df = df.iloc[page_offset : page_offset + page_size]

    return df, rows


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
    df, _ = get_file_dataframe(driver, path)

    # do we apply a new schema?
    if new_schema:
        df = analitico.schema.apply_schema(df, new_schema)

    # what format do we write to?
    new_suffix = Path(new_path if new_path else path).suffix.lower()

    # write dataframe to a temp file then upload to storage path
    with tempfile.NamedTemporaryFile(mode="w+", prefix="df_", suffix=new_suffix) as f:
        if new_suffix in CSV_SUFFIXES:
            df.to_csv(f.name, index=False)
        elif new_suffix in PARQUET_SUFFIXES:
            # TODO add index=False after updating pandas to > 0.24
            df.to_parquet(f.name)
        elif new_suffix in EXCEL_SUFFIXES:
            df.to_excel(f.name, index=False)
        elif new_suffix in HDF_SUFFIXES:
            df.to_hdf(f.name, key="df", mode="w")
        else:
            raise AnaliticoException(f"Unknown format for {path}.", status_code=status.HTTP_400_BAD_REQUEST)

        driver.upload(f.name, new_path if new_path else path)

        # file has moved to new location?
        if new_path and path != new_path:
            driver.delete(path)

    return True
