
# Given an order, order details, customer and store information the regressor 
# estimates how long it will take in minutes to pick the given shopping list at
# the store and deliver it to the customer's home
#
# Copyright (C) 2018 by Analitico.ai
# All rights reserved

import analitico.models
import analitico.utilities

class OrderTimeModel(analitico.models.TabularRegressorModel):

    def __init__(self, settings):
        super().__init__(settings)
        analitico.utilities.logger.info('OrderTimeModel.__init__')

    def _train_preprocess_records(self, df):
        """ Remove outliers and sort dataset before it's used for training """
        df = super()._train_preprocess_records(df)
        analitico.utilities.logger.info('OrderTimeModel.train_filter_records')
        df = df[(df['total_min'] is not None) and (df['total_min'] < 120)]
        df = df.sort_values(by=['order_deliver_at_start'], ascending=True)
        return df
