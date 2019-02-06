"""
Plugins that group other plugins into logical groups like
ETL (extract, transform, load) pipeline or a graph used to
process data and create a machine learning model.
"""

from .plugin import IGroupPlugin

##
## PipelinePlugin
##


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

    def run(self, *args, **kwargs):
        """ Process plugins in sequence, return combinined chained result """
        for plugin in self.plugins:
            # a plugin can have one or more input parameters and one or more
            # output parameters. results from a call to the next in the chain
            # are passed as tuples. when we finally return, if we have a single
            # result we unpackit, otherwise we return as tuple. this allows
            # a pipeline of plugins to chain plugins with a variable number of
            # parameters. each plugin is responsible for validating the type of
            # its input positional parameters and named parameters.
            args = plugin.run(*args, **kwargs)
            if not isinstance(args, tuple):
                args = (args,)
        return args if len(args) > 1 else args[0]
