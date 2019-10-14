""" Utility methods to convert between pandas and analitico's schemas """

import numpy as np
import pandas as pd

from analitico import AnaliticoException

##
## Schema
##

# pandas types for analitico's types
PD_TYPE_INTEGER = "int64"
PD_TYPE_FLOAT = "float64"
PD_TYPE_STRING = "str"
PD_TYPE_BOOLEAN = "bool"
PD_TYPE_DATETIME = "datetime64"
PD_TYPE_TIMESPAN = "timedelta64"
PD_TYPE_CATEGORY = "category"

ANALITICO_TYPE_INTEGER = "integer"
ANALITICO_TYPE_FLOAT = "float"
ANALITICO_TYPE_STRING = "string"
ANALITICO_TYPE_BOOLEAN = "boolean"
ANALITICO_TYPE_DATETIME = "datetime"
ANALITICO_TYPE_TIMESPAN = "timespan"
ANALITICO_TYPE_CATEGORY = "category"

# these values are replaced with pd.NaN
NA_VALUES = [
    "None",
    "",
    "#N/A",
    "#N/A",
    "N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "N/A",
    "NA",
    "NULL",
    "NaN",
    "n/a",
    "nan",
    "null",
]

# these values are replaced with pd.NaT
NA_DATES = NA_VALUES + [0, "0"]


def analitico_to_pandas_type(data_type: str):
    """ Converts an analitico data type to the equivalent dtype string for pandas dataframes """
    try:
        ANALITICO_TO_PANDAS_TYPES = {
            ANALITICO_TYPE_STRING: PD_TYPE_STRING,
            ANALITICO_TYPE_INTEGER: PD_TYPE_INTEGER,
            ANALITICO_TYPE_FLOAT: PD_TYPE_FLOAT,
            ANALITICO_TYPE_BOOLEAN: PD_TYPE_BOOLEAN,
            ANALITICO_TYPE_DATETIME: PD_TYPE_DATETIME,
            ANALITICO_TYPE_TIMESPAN: PD_TYPE_TIMESPAN,
            ANALITICO_TYPE_CATEGORY: PD_TYPE_CATEGORY,
        }
        return ANALITICO_TO_PANDAS_TYPES[data_type]
    except KeyError as exc:
        raise KeyError("analitico_to_pandas_type - unknown type: " + data_type, exc)


def pandas_to_analitico_type(data_type):
    """ Return the analitico schema data type of a pandas dtype """
    if data_type == "int" or data_type == "int8":
        return ANALITICO_TYPE_INTEGER
    if data_type == "float":
        return ANALITICO_TYPE_FLOAT
    if data_type == "bool":
        return ANALITICO_TYPE_BOOLEAN
    if data_type.name == "category":
        return ANALITICO_TYPE_CATEGORY  # dtype alone doesn't ==
    if data_type == "object":
        return ANALITICO_TYPE_STRING
    if data_type == "datetime64[ns]":
        return ANALITICO_TYPE_DATETIME
    if data_type == "timedelta64[ns]":
        return ANALITICO_TYPE_TIMESPAN
    raise KeyError("_pandas_to_analitico_type - unknown data_type: " + str(data_type))


def get_column_type(df, column):
    """ Returns analitico's column type for the column with given name """
    return pandas_to_analitico_type(df[column].dtype)


def generate_schema(df: pd.DataFrame) -> dict:
    """ Generates an analitico schema from a pandas dataframe """
    columns = []

    columns_names = df.columns.tolist()
    for name in columns_names:
        ctype = pandas_to_analitico_type(df[name].dtype)
        column = {"name": name, "type": ctype}
        if df.index.name == name:
            column["index"] = True
        columns.append(column)
    return {"columns": columns}


def apply_column(df: pd.DataFrame, column):
    """ Apply given type to the column (parameters are type, name, etc from schema column) """
    try:
        assert isinstance(df, pd.DataFrame)
        assert "name" in column, "apply_column - should always be passed a column name"
        column_name = column["name"]

        # we are being requested to apply type to the column
        if "type" in column:
            try:
                column_type = column["type"]
                missing = column_name not in df.columns
                if column_type == "string":
                    if missing:
                        df[column_name] = None
                    df[column_name] = df[column_name].astype(str)
                elif column_type == "float":
                    if missing:
                        df[column_name] = np.nan
                    df[column_name].fillna(0)
                    df[column_name] = df[column_name].astype(float)
                elif column_type == "boolean":
                    if missing:
                        df[column_name] = False
                    # missing values are converted to False
                    df[column_name] = df[column_name].fillna(False).astype(bool)
                elif column_type == "integer":
                    if missing:
                        df[column_name] = 0
                    # missing values converted to 0
                    df[column_name] = df[column_name].fillna(0).astype(int)
                elif column_type == "datetime":
                    if missing:
                        df[column_name] = None
                    else:
                        # strings like no
                        for not_a_date in NA_DATES:
                            df[column_name].replace(not_a_date, np.nan, inplace=True)
                    df[column_name] = df[column_name].astype("datetime64[ns]")
                elif column_type == "timespan":
                    if missing:
                        df[column_name] = None
                    df[column_name] = pd.to_timedelta(df[column_name])
                elif column_type == "category":
                    if missing:
                        df[column_name] = None
                    df[column_name] = df[column_name].astype("category")
                else:
                    raise Exception("apply_column - unknown type: " + column_type)
            except Exception as exc:
                msg = f"apply_column - exception while applying type {column_type} to column {column_name}"
                raise AnaliticoException(msg)

        if "rename" in column:
            df.rename(index=str, columns={column_name: column["rename"]}, inplace=True)
            column_name = column["rename"]

        # make requested column index
        index = column.get("index", False)
        if index:
            # we use this column as the index but do not remove it from
            # the columns otherwise we won't be able to rename it, etc
            df.set_index(column_name, drop=False, inplace=True)

        assert column_name in df.columns
        return df[column_name]

    except AnaliticoException as exc:
        raise

    except Exception as exc:
        raise AnaliticoException(f"apply_column - could apply {column}") from exc


def apply_schema(df: pd.DataFrame, schema):
    """ 
    Applies the given schema to the dataframe. The method will scan columns
    in the schema and apply their type to columns in the dataframe. It will
    then sort, filter and rename columns according to schema.
    """
    assert isinstance(df, pd.DataFrame), "apply_schema should be passed a pd.DataFrame, received: " + str(df)
    assert isinstance(schema, dict), "apply_schema should be passed a schema dictionary"

    # when a schema contains the 'columns' array, it means that we should
    # apply the given columns transformations and end up with a dataframe
    # containing only the given columns, ordered as specified. if the dataframe
    # has any additional columns not listed in 'columns' they will be dropped.
    if "columns" in schema:
        # select columns and apply types to columns
        names = []
        for column in schema["columns"]:
            ds = apply_column(df, column)
            names.append(ds.name)
        # reorder and remove extra columns
        return df[names]

    # when a schema contains the 'apply' array it means that we should
    # apply the given column transformations to the dataframe. the array
    # may or just one or a few columns, meaning all other columns are left
    # as is. the order of items in 'apply' does not need to match the order
    # in the dataframe
    if "apply" in schema:
        for column in schema["apply"]:
            apply_column(df, column)

    # if schema has a "drop" array then the columns
    if "drop" in schema:
        for column in schema["drop"]:
            column_name = column.get("name")
            if column_name and column_name in df.columns:
                df.drop(columns=[column_name], inplace=True)

    return df
