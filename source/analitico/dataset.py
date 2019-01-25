
import pandas as pd
import numpy as np

##
## Utilities
##

def analitico_to_pandas_type(type: str):
    """ Converts an analitico data type to the equivalent dtype string for pandas dataframes """
    ANALITICO_TO_PANDAS_TYPES = {
        'string': 'str',
        'integer': 'int64',
        'float': 'float64',
        'boolean': 'bool',
        'datetime': 'datetime64',
        'timespan': 'timedelta64',
        'category': 'category'
    }
    return ANALITICO_TO_PANDAS_TYPES[type]

def pandas_to_analitico_type(dtype):
    """ Return the analitico schema data type of a pandas dtype """
    if dtype == 'int': return 'integer'
    if dtype == 'float': return 'float'
    if dtype == 'bool': return 'boolean'
    if dtype.name == 'category': return 'category' # dtype alone doesn't ==
    if dtype == 'object': return 'string'
    if dtype == 'datetime64[ns]': return 'datetime'
    if dtype == 'timedelta64[ns]': return 'timespan'
    raise KeyError('pandas_to_analitico_type - unknown dtype: ' + str(dtype))

##
## DatasetSource
##

class DatasetSource:
    """ A generic dataset source """

    settings: dict = None

    def __init__(self, **kwargs):
        self.settings = kwargs

    def get_dataframe(**kwargs):
        return None

##
## CsvDatasetSource
##

class CsvDatasetSource(DatasetSource):
    """ Creates a pandas dataset from a CSV file """

    def get_dataframe(self, **kwargs):
        """ Creates a pandas dataframe from the csv source """
        try:
            schema = self.settings.get('schema')
            columns = schema.get('columns') if schema else None

            dtype = None
            parse_dates = None
            index = None

            if columns:
                dtype = {}
                parse_dates = []
                for idx, column in enumerate(columns):
                    if column['type'] == 'datetime':
                        parse_dates.append(idx) # ISO8601 dates only
                    elif column['type'] == 'timespan':
                        # timedelta needs to be applied later on or else we will get
                        # 'the dtype timedelta64 is not supported for parsing'
                        dtype[column['name']] = 'object'
                    else:
                        dtype[column['name']] = analitico_to_pandas_type(column['type'])
                    if column.get('index', False):
                        index = column['name']

            url = self.settings['url']
            df = pd.read_csv(url, dtype=dtype, parse_dates=parse_dates, **kwargs)

            if index: 
                # transform specific column with unique values to dataframe index
                df = df.set_index(index, drop=False)    

            if columns:
                names = []
                for column in columns:
                    # check if we need to cast timedelta which we had left as strings
                    if column['type'] == 'timespan':
                        name = column['name']
                        df[name] = pd.to_timedelta(df[name])
                    names.append(column['name'])
                # reorder and filter columns as requested in schema
                df = df[names]

            return df
        except Exception as exc:
            raise exc

##
## Dataset
##

class Dataset:
    """ A dataset can retrieve data from a source and process it through a pipeline to generate a dataframe """

    settings:dict = None

    def __init__(self, **kwargs):
        self.settings = kwargs

    @property
    def id(self) -> str:
        return self.settings.get('id')

    def get_dataframe(self, **kwargs):
        """ Creates a pandas dataframe from the source of this dataset """
        source_settings = self.settings['source']
        source = ds_source_factory(source_settings)
        return source.get_dataframe(**kwargs)

    @staticmethod
    def generate_schema(df: pd.DataFrame) -> dict:
        """ Generates an analitico schema from a pandas dataframe """
        columns = []
        for name in df.columns:
            column = {
                'name': name,
                'type': pandas_to_analitico_type(df[name].dtype)
            }
            if df.index.name == name:
                column['index'] = True
            columns.append(column)
        return { 'columns': columns }

##
## Factory
##   

def ds_factory(**kwargs):
    return Dataset(**kwargs)


def ds_source_factory(settings: dict):
    """ Create a datasource from its settings configuration """
    if settings['type'] == 'text/csv':
        return CsvDatasetSource(**settings)
    raise NotImplementedError("DatasetSource for type '" + settings['type'] + "' is not implemented.")
