
import pandas as pd
import numpy as np

##
## Utilities
##

# Map used to convert analitico schema types to pandas
ANALITICO_TO_PANDAS_TYPES = {
    'string': 'str',
    'integer': 'int64',
    'float': 'float64',
    'boolean': 'bool',
    'datetime': 'datetime64',
    'timespan': 'timedelta',
    'category': 'category'
}

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
            dtype = None
            parse_dates = None

            if 'schema' in self.settings:
                schema = self.settings['schema']
                if 'columns' in schema:
                    dtype = {}
                    parse_dates = []
                    for idx, column in enumerate(schema['columns']):
                        if column['type'] == 'datetime':
                            parse_dates.append(idx) # ISO8601 dates only
                        else:
                            dtype[column['name']] = ANALITICO_TO_PANDAS_TYPES[column['type']]

            url = self.settings['url']
            return pd.read_csv(url, dtype=dtype, parse_dates=parse_dates, **kwargs)
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
