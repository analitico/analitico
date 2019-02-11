from analitico.utilities import get_dict_dot


class AnaliticoModel:
    """ Base class for machine learning models """

    # Unique project id used for tracking, directories, access, billing, eg: s24-order-sorting
    project_id: str = None

    # Project settings
    settings: dict = None

    # Training information (as returned by previous call to train)
    training: dict = None

    # True if we're debugging (add extra info, etc)
    debug: bool = True

    # True if results should be uploaded after training
    upload: bool = True

    def __init__(self, settings: dict):
        self.project_id = settings.get("project_id")
        self.settings = settings

    def get_setting(self, key, default=None):
        """ Returns setting value expressed in dotted notation or default value, eg: data.assets.model_url """
        if not self.settings:
            return default
        value = get_dict_dot(self.settings, "request." + key)
        return value if value else get_dict_dot(self.settings, key, default)

    ##
    ## utility methods
    ##

    def upload_asset(name, asset):
        pass

    def download_asset(name):
        pass

    ##
    ## main methods
    ##

    def train(self, training_id) -> dict:
        """ Trains machine learning model and returns a dictionary with the training's results """
        raise NotImplementedError()

    def predict(self, data) -> dict:
        """ Runs prediction on given data, returns predictions and metadata """
        raise NotImplementedError()
