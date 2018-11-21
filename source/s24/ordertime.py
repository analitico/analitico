
# Given an order, order details, customer and store
# information the regressor estimates how long it will
# take in minutes to pick the given shopping list at
# the store and deliver it to the customer's home
#
# Copyright (C) 2018 by Analitico.ai
# All rights reserved

from analitico.models import AnaliticoTabularRegressorModel


TRAINING_CSV_PATH = 'data/s24/training/orders-joined.csv'


class OrderTimeModel(AnaliticoTabularRegressorModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('OrderTimeModel')
        self.project_id = 's24-order-time'
        self.models_dir = 'data/s24/models/order-time'

    def train(self):
        return self._train(TRAINING_CSV_PATH)
