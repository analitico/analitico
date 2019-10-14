import pandas as pd

import analitico.mixin

##
## DEPRECATED. VERSION USED BY SDK IS IN MODELS/DATASET
##


class Dataset(analitico.mixin.AttributeMixin):
    """ A dataset can retrieve data from a source and process it through a pipeline to generate a dataframe """

    plugin = None

    def __init__(self, factory=None, **kwargs):
        super().__init__(**kwargs)
        if "plugin" in kwargs:
            if not factory:
                raise Exception("Dataset should be initialized with a factory so it can create plugins")
            self.plugin = kwargs["plugin"]
            if isinstance(self.plugin, dict):
                self.plugin = factory.get_plugin(**self.plugin)

    def get_dataframe(self, **kwargs):
        """ Creates a pandas dataframe from the plugin of this dataset (usually a source or pipeline) """
        if self.plugin:
            df = self.plugin.run(**kwargs)
            assert isinstance(df, pd.DataFrame)
            return df
        return None
