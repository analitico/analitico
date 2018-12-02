# Utility methods to process dataframes and simplify workflow.
# Copyright (C) 2018 by Analitico.ai. All rights reserved.

import time
import pandas as pd
import json
import logging
import holidays

from catboost import Pool
from datetime import datetime

# default logger for analitico's libraries
logger = logging.getLogger('analitico')

__all__ = [
    "timestamp_to_time",
    "augment_timestamp_column",
    "dataframe_to_catpool"
]


def save_json(data, filename, indent=4):
    """ Saves given data in a json file (prettified by default) """
    with open(filename, 'w') as f:
        json.dump(data, f, indent=indent)

def read_json(filename):
    """ Reads, decodes and returns the contents of a json file """
    with open(filename) as f:
        return json.load(f)

def time_ms(started_on=None):
    """ Returns the time elapsed since given time in ms """
    return datetime.now() if started_on is None else int((datetime.now() - started_on).total_seconds() * 1000)

def time_it(code):
    """ Returns the time elapsed to execute the given call in ms """
    started_on = datetime.now()
    code()
    return int((datetime.now() - started_on).total_seconds() * 1000)


# holiday calendar
_it_holidays = holidays.Italy()


def timestamp_to_time(ts: str, ts_format="%Y-%m-%d %H:%M:%S") -> time.struct_time:
    """ Converts a timestamp string in the given format to a time object """
    return time.strptime(ts, ts_format)


def timestamp_to_secs(ts: str, ts_format="%Y-%m-%d %H:%M:%S") -> float:
    """ Converts a timestamp string to number of seconds since epoch """
    return time.mktime(time.strptime(ts, ts_format))


def timestamp_diff_secs(ts1, ts2):
    t1 = timestamp_to_secs(ts1)
    t2 = timestamp_to_secs(ts2)
    return t1 - t2


def augment_timestamp_column(df: pd.DataFrame, col: str, ts_format="%Y-%m-%d %H:%M:%S") -> pd.DataFrame:
    """ Expand a timestamp column into a number of separate columns
        with the year, month [1,12], hour [0,23], minute [0,59], 
        weekday [0,6] and day of the year [1,366]. The name of the 
        new columns follows the name of the original column with
        the _year, _month, _hour, _min, _wday and _yday suffixes appended. """
    # https://docs.python.org/3/library/time.html#module-time
    df[col+'_year'] = df[col].map(lambda ts: timestamp_to_time(ts, ts_format).tm_year)
    df[col+'_month'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_mon)
    df[col+'_day'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_mday) #.astype(CategoricalDtype(range(1,31),ordered=True))
    df[col+'_hour'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_hour)
    df[col+'_min'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_min)
    df[col+'_weekday'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_wday) #.astype(CategoricalDtype(range(0,6),ordered=True))
    df[col+'_yearday'] = df[col].map(lambda ts: timestamp_to_time(ts).tm_yday) #.astype(CategoricalDtype(range(1,366),ordered=True))
    df[col+'_holyday'] = df[col].map(lambda ts: int(ts[:10] in _it_holidays))
    return df   


def dataframe_to_catpool(df: pd.DataFrame, features, categorical_features=None, timestamp_features=None, label_feature=None):
    """ Takes a pandas dataframe and prepares a catboost pool to be used for training or prediction.
        df: The source dataframe
        features: An array of names of columns to be used as features
        categorical_features: An array of names of categorical features
        timestamp_features: Timestamp features will be augmented
        label_feature: If specified, the labels (eg: regression targets) are extracted and returned
        Returns: A catboost Pool and the column with the labels (if specified)
    """
    categorical_features = categorical_features.copy()
    df = df.copy()
    # save labels column
    df_labels = df[label_feature] if label_feature is not None else None
    # reorder columns, drop unused 
    df = df[features]

    for categorical_feature in categorical_features:
        df[categorical_feature].astype(str)
        df = df.fillna(value={ categorical_feature: '' })

    # augment timestamps
    if timestamp_features is not None:
        for timestamp_feature in timestamp_features:
            df = augment_timestamp_column(df, timestamp_feature)
            df = df.drop(columns=timestamp_feature)
            categorical_features.append(timestamp_feature + '_year')
            categorical_features.append(timestamp_feature + '_month')
            categorical_features.append(timestamp_feature + '_day')
            categorical_features.append(timestamp_feature + '_weekday')
            categorical_features.append(timestamp_feature + '_holiday')

    # indexes of columns with categorical features
    categorical_idx = [df.columns.get_loc(c) for c in df.columns if c in categorical_features]
    df2 = df.copy()
    pool = Pool(df2, df_labels, cat_features=categorical_idx)
    return pool, df_labels


def get_dict_dot(d:dict, key:str):
    """ Gets an entry from a dictionary using dot notation key, eg: this.that.something """
    try:
        if d and key:
            split = key.split('.')
            value = d[split[0]]
            if value:
                if len(split) == 1:
                    return value
                return get_dict_dot(value, key[len(split[0])+1:])
    except KeyError:
        pass
    return None
