
import pandas
from .plugin import IDataframePlugin, PluginException

##
## CodeDataframePlugin
##

class CodeDataframePlugin(IDataframePlugin):
    """
    A plugin that can apply some generic python code to a dataframe and return it.
    Normally a short bit of code is used to apply expressions using pandas or to filter
    rows and such. The dataframe can be accessed in the code snippet using the variable
    'df' and returned in the same variable. The code snipped is passed to the plugin
    using the setting 'code' containing the code itself. This plugin is not isolating
    the code therefore it should only run internal code or it will expose a security risk.
    Later on we will create a version of this plugin that uses dockers to isolate the code.
    """
    class Meta(IDataframePlugin.Meta):
        name = 'analitico.plugin.codedataframeplugin'

    def process_df(self, df, **kwargs) -> pandas.DataFrame:
        """ Apply some python code to the dataframe """
        code = self.get_setting('code', None)
        if code:
            try:
                # TODO plugin should restrict code execution to math, numpy and pandas #17
                # https://www.programiz.com/python-programming/methods/built-in/exec
                exec(code)
            except Exception as exc:
                message = 'An error occoured while executing "{0}": "{1}".'.format(code, exc)
                self.logger.error(message)
                raise PluginException(message, self, exc)
        return df
