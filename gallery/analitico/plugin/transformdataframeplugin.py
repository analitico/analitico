import pandas as pd

from analitico.schema import apply_schema
from .interfaces import IDataframePlugin, plugin

##
## TransformDataframePlugin
##


@plugin
class TransformDataframePlugin(IDataframePlugin):
    """
    TransformDataframePlugin can apply a schema to a dataframe and can be used to:
    - drop columns you don't need
    - apply a type to a column (eg. change a string to a date)
    - reorder columns in a dataframe (eg. put the label last)
    - rename columns
    - make a column the index of the dataframe
    """

    class Meta(IDataframePlugin.Meta):
        name = "analitico.plugin.TransformDataframePlugin"
        title = "TransformDataframePlugin"
        description = "This plugin applies a schema to the input dataframe to provide a variety of transformations."
        configurations = [
            {
                "name": "schema",
                "type": "analitico/schema",
                "optional": False,
                "description": "The schema is applied to the input dataframe. The choice and attributes "
                + "of columns indicate how they are filtered, ordered, cast, etc.",
            }
        ]

    def run(self, *args, action=None, **kwargs) -> pd.DataFrame:

        df = args[0]
        if not isinstance(df, pd.DataFrame):
            self.warning("TransformDataframePlugin - requires a single pd.DataFrame as input, none was found")
            return args

        schema = self.get_attribute("schema", None)
        if not schema:
            self.warning(
                "TransformDataframePlugin - should have a 'schema' attribute with the schema that you want to apply to the input dataframe"
            )
            return df

        df = apply_schema(df, schema)
        self.info("TransformDataframePlugin - schema applied to dataframe")

        return df
