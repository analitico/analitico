from .plugin import IGroupPlugin

##
## PipelinePlugin
##


class GraphPlugin(IGroupPlugin):
    """ A plugin that can join a number of other plugins into a coordinated workflow. """

    class Meta(IGroupPlugin.Meta):
        name = "analitico.plugin.GraphPlugin"

    def run(self, *args, **kwargs):
        raise NotImplementedError()
