"""
Plugins that group other plugins into logical groups like
ETL (extract, transform, load) pipeline or a graph used to
process data and create a machine learning model.
"""

import pandas as pd
import analitico.pandas

from analitico import status, AnaliticoException
from analitico.pandas import pd_to_dict
from analitico.utilities import time_ms
from analitico.schema import pandas_to_analitico_type, generate_schema
from analitico.constants import ACTION_PREDICT

from .interfaces import IGroupPlugin, plugin

##
## PipelinePlugin
##

DATAFRAME_SAMPLES = 10


@plugin
class PipelinePlugin(IGroupPlugin):
    """ 
    A plugin that creates a linear workflow by chaining together other plugins.
    Plugins that are chained in a pipeline need to take a single input and have
    a single output of the same kind so they same object can be processed from 
    the first, to the next and down to the last, then returned to caller as if
    the process was just one logical operation. PipelinePlugin can be used to 
    for example to construct ETL (extract, transform, load) workflows.
    """

    class Meta(IGroupPlugin.Meta):
        name = "analitico.plugin.PipelinePlugin"

    def get_metadata(self, *args):
        """ Transform list of arguments into a dictionary describing them (used to log status, etc) """
        output = []
        if args and len(args) > 0:
            for i, arg in enumerate(args):
                meta = {}
                meta["type"] = str(type(arg))
                if isinstance(arg, pd.DataFrame):
                    df = arg
                    meta["rows"] = len(df)
                    meta["schema"] = generate_schema(df)
                    samples = analitico.pandas.pd_sample(df, DATAFRAME_SAMPLES)
                    meta["samples"] = pd_to_dict(samples)

                    # debugging help
                    self.factory.debug("output[%d]: pd.DataFrame", i)
                    self.factory.debug("  rows: %d", len(df))
                    self.factory.debug("  columns: %d", len(df.columns))
                    for j, column in enumerate(df.columns):
                        self.factory.debug(
                            "  %3d %s (%s/%s)", j, column, df.dtypes[j], pandas_to_analitico_type(df.dtypes[j])
                        )
                else:
                    self.factory.debug("output[%d]: %s", i, str(type(arg)))
                output.append(meta)
        return output

    def run(self, *args, action=None, **kwargs):
        """ Process plugins in sequence, return combined result """
        try:
            pipeline_on = time_ms()

            # logging is expensive so we don't track everything in prediction mode
            predicting = action and ACTION_PREDICT in action
            if not predicting:
                self.factory.status(self, status.STATUS_RUNNING)

            for p, plugin in enumerate(self.plugins):
                plugin_on = time_ms()
                if not predicting:
                    self.factory.status(plugin, status.STATUS_RUNNING)

                # a plugin can have one or more input parameters and one or more
                # output parameters. results from a call to the next in the chain
                # are passed as tuples. when we finally return, if we have a single
                # result we unpackit, otherwise we return as tuple. this allows
                # a pipeline of plugins to chain plugins with a variable number of
                # parameters. each plugin is responsible for validating the type of
                # its input positional parameters and named parameters.
                try:
                    args = plugin.run(*args, action=action, **kwargs)
                    if not isinstance(args, tuple):
                        args = (args,)
                except Exception as e:
                    self.factory.status(plugin, status.STATUS_FAILED, exception=e)
                    raise

                # log outputs of plugin
                # TODO skip when predicting
                if not predicting:
                    output = self.get_metadata(*args)
                    self.factory.status(plugin, status.STATUS_COMPLETED, elapsed_ms=time_ms(plugin_on), output=output)

            if not predicting:
                # log outputs of pipeline
                self.factory.status(self, status.STATUS_COMPLETED, elapsed_ms=time_ms(pipeline_on), output=output)
            return args if len(args) > 1 else args[0]

        except Exception as e:
            self.factory.status(self, status.STATUS_FAILED)
            self.factory.exception(self.Meta.name + " failed while processing", item=self, exception=e)
