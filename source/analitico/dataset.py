
import pandas as pd
import numpy as np

##
## DatasetSource
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

def type_analitico_to_pandas(type: str):
    return ANALITICO_TO_PANDAS_TYPES[type]

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
        try:
            url = self.settings['url']

            dtype = None

            if 'schema' in self.settings:
                schema = self.settings['schema']
                if 'columns' in schema:
                    columns = schema['columns']
                    dtype = { column['name']: ANALITICO_TO_PANDAS_TYPES[column['type']] for column in columns }

            return pd.read_csv(url, dtype=dtype, **kwargs)
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

class DatasetFactory():
    """ Factory used to create datasets with various methods """

    @staticmethod
    def from_settings(settings: dict):
        return Dataset(settings)

    @staticmethod
    def from_id(dataset_id):
        return None


def ds_source_factory(settings: dict):
    """ Create a datasource from its settings configuration """
    if settings['type'] == 'text/csv':
        return CsvDatasetSource(**settings)
    raise NotImplementedError("DatasetSource for type '" + settings['type'] + "' is not implemented.")


def ds_dataset_factory(dataset_id: str = None, token: str = None, endpoint: str = None):
    return Dataset(id = dataset_id)

