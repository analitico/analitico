
# Given an order, order details, customer and store
# information the regressor estimates how long it will
# take in minutes to pick the given shopping list at
# the store and deliver it to the customer's home
#
# Copyright (C) 2018 by Analitico.ai
# All rights reserved

from analitico.utilities import logger
from analitico.models import TabularRegressorModel


class OrderTimeModel(TabularRegressorModel):

    def __init__(self, settings):
        super().__init__(settings)
        logger.info('OrderTimeModel.__init__')

    def train(self, training_id):
        logger.info('OrderTimeModel.train: %s' % training_id)
        return super().train(training_id)
