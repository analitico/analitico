import pandas as pd
import json
import dateutil
from io import StringIO

import analitico
import analitico.schema
import analitico.utilities

from analitico import AnaliticoException, logger
from analitico.schema import analitico_to_pandas_type, NA_VALUES

##
## Pandas utilities
##


def pd_print_nulls(df):
    for column in df:
        nulls = df[column].isnull().sum()
        if nulls > 0:
            perc = 100.0 * nulls / len(df)
            print("{0} has {1} null values {2:1.2f}%".format(column, nulls, perc))


def pd_date_parser(x):
    if not x:
        return None
    lower_x = x.lower()
    if lower_x in ("none", "null", "nan", "empty"):
        return None
    date = dateutil.parser.parser(x)
    return date


def pd_cast_datetime(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """ Casts a string column to a date column, assumes format is recognizable """
    df[column] = pd.to_datetime(df[column], infer_datetime_format=True, errors="coerce")
    return df


def move_column(df: pd.DataFrame, column: str, index=0) -> pd.DataFrame:
    """ Moves the column with the given name to the given index, returns dataframe """
    columns = list(df.columns)
    if column not in columns:
        logger.warning(f"move_column - column {column} is not present in df.columns: {df.columns}")
        return df
    columns.insert(index, columns.pop(columns.index(column)))
    return df[columns]


EXPAND_ALL_COLUMNS = ["dayofweek", "year", "month", "day", "hour", "minute"]


def augment_dates(df: pd.DataFrame, column: str = None, expand=None, drop=True) -> pd.DataFrame:
    """
    Augment the specific column contaning dates into a number of separate columns with the day of the week,
    year, month, day, hour and minute. If a column name is not specified, the method will expand all columns
    of type datetime. If a column is specified but it's not of type datetime, the column will be converted to
    datetime. The expanded column is the dropped from the dataframe unless otherwise specified.
    """
    try:
        if not isinstance(df, pd.DataFrame):
            raise AnaliticoException("augment_dates - requires a pd.DataFrame")

        # if a specific column was not specified we scan all columns and
        # apply date augmentation to all columns of type datetime
        if not column:
            # TODO figure out why analitico.schema.PD_TYPE_DATETIME doesn't work
            for col1 in df.columns.copy():
                if df[col1].dtype == "datetime64[ns]":
                    df = augment_dates(df, col1, expand, drop)
            return df

        if column not in df.columns:
            raise AnaliticoException(f"augment_dates - cannot find column {column} in df.columns: {df.columns}")

        if df[column].dtype != analitico.schema.PD_TYPE_DATETIME:
            logger.info(
                f"augment_dates - changing column {column} from type {df[column].dtype} to {analitico.schema.PD_TYPE_DATETIME}"
            )
            df = pd_cast_datetime(df, column)

        # TODO warn of missing date fields, log number of missing records

        if not expand:
            expand = EXPAND_ALL_COLUMNS

        loc = df.columns.get_loc(column) + 1
        dates = pd.DatetimeIndex(df[column])
        if "dayofweek" in expand:
            df[column + ".dayofweek"] = dates.dayofweek.astype("category")
            df = move_column(df, column + ".dayofweek", loc)
            loc += 1
        if "year" in expand:
            df[column + ".year"] = dates.year.astype("category")
            df = move_column(df, column + ".year", loc)
            loc += 1
        if "month" in expand:
            df[column + ".month"] = dates.month.astype("category")
            df = move_column(df, column + ".month", loc)
            loc += 1
        if "day" in expand:
            df[column + ".day"] = dates.day.astype("category")
            df = move_column(df, column + ".day", loc)
            loc += 1
        if "hour" in expand:
            df[column + ".hour"] = dates.hour.astype("category")
            df = move_column(df, column + ".hour", loc)
            loc += 1
        if "minute" in expand:
            df[column + ".minute"] = dates.minute.astype("category", copy=False)
            df = move_column(df, column + ".minute", loc)
            loc += 1

        if drop:
            df = df.drop([column], axis=1, inplace=False)

    except AnaliticoException:
        raise
    except Exception as exc:
        raise AnaliticoException(
            f"augment_dates - an error occoured while augmenting dates in column {column}"
        ) from exc

    return df


# DEPRECATED
def pd_augment_date(df, column):
    """ Augments a datetime column into year, month, day, dayofweek, hour, minute """
    if column not in df.columns:
        raise Exception("pd_augment_date - column '" + column + "' is missing")
    # create separate columns for each parameter (overwrite if needed)
    dates = pd.DatetimeIndex(df[column])
    df[column + ".year"] = dates.year.astype("category", copy=False)
    df[column + ".month"] = dates.month.astype("category", copy=False)
    df[column + ".day"] = dates.day.astype("category", copy=False)
    df[column + ".hour"] = dates.hour.astype("category", copy=False)
    df[column + ".minute"] = dates.minute.astype("category", copy=False)
    df[column + ".dayofweek"] = dates.dayofweek.astype("category", copy=False)
    # TODO place augmented columns next to original
    # loc = df.columns.get_loc(column) + 1
    # df.drop([column], axis=1, inplace=True)


def pd_timediff_min(df, column_start, column_end, column_diff):
    """ Creates a new column with difference in minutes between the two named columns """
    pd_cast_datetime(df, column_start)
    pd_cast_datetime(df, column_end)
    df[column_diff] = df[column_end] - df[column_start]
    df[column_diff] = df[column_diff].dt.total_seconds() / 60.0


def pd_columns_to_string(df):
    """ Returns a single string with a list of columns, eg: 'col1', 'col2', 'col3' """
    columns = "".join("'" + column + "', " for column in df.columns)
    return columns[:-2]


def pd_read_csv(filepath_or_buffer, schema=None, skiprows=None, nrows=None):
    """ Read csv file from file or stream and apply optional schema """
    try:
        dtype = None

        if schema:
            # array of types for each column in the source
            columns = schema.get("columns")
            if columns:
                dtype = {}
                for column in columns:
                    if "type" in column:  # type is optionally defined
                        if column["type"] == "datetime":
                            dtype[column["name"]] = "object"
                        elif column["type"] == "timespan":
                            dtype[column["name"]] = "object"
                        elif column["type"] == "integer":
                            pass  # do not cast so we can deal with nulls later
                        else:
                            dtype[column["name"]] = analitico_to_pandas_type(column["type"])

        # read csv from file or stream
        df = pd.read_csv(
            filepath_or_buffer,
            dtype=dtype,
            encoding="utf-8",
            na_values=NA_VALUES,
            low_memory=False,
            skiprows=skiprows,
            nrows=nrows,
        )

        if schema:
            # reorder, filter, apply types, rename columns as requested in schema
            df = analitico.schema.apply_schema(df, schema)
        return df

    except Exception as exc:
        logger.error(f"Could not read csv file from {filepath_or_buffer}, schema: {schema}, dtype: {dtype}")
        raise exc


def pd_to_csv(df: pd.DataFrame, filename, schema=False, samples=0):
    """ Writes dataframe to disk optionally adding a .schema file and a .samples file """
    if not filename.endswith(".csv"):
        raise Exception("pd_to_csv - filename " + filename + " should end in .csv")
    df.to_csv(filename, encoding="utf-8")
    if schema:
        schema = analitico.schema.generate_schema(df)
        schemaname = filename + ".info"
        analitico.utilities.save_json({"schema": schema}, schemaname)
    if samples > 0 and not df.empty:
        samples = pd_sample(df, samples)
        samplesname = filename[:-4] + ".samples.csv"
        samples.to_csv(samplesname, encoding="utf-8")


def pd_drop_column(df, column, inplace=False):
    """ Drops a column, no exceptions if it's not there """
    try:
        return df.drop([column], axis=1, inplace=inplace)
    except:
        logger.warning(f"pd_drop_column - could not find column {column}")
    return df


def pd_to_dict(df):
    """ Convert a dataframe to json, encodes all dates and timestamps to ISO8601 """
    assert isinstance(df, pd.DataFrame), "pd_to_dict - requires a pd.DataFrame"
    with StringIO() as io:
        df.to_json(io, orient="records", date_format="iso", date_unit="s", double_precision=6)
        io.seek(0)
        return json.load(io)


def pd_sample(df, n=20):
    """ Returns a sample from the given DataFrame, either number of rows or percentage. """
    if n < 1:
        return df.sample(frac=n)
    if n < len(df.index):
        return df.sample(n=n)
    return df
