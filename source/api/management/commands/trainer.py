
import os
import time

import analitico.utilities
import api.models

from api.models import Training
from api.views import get_project_model

from analitico.utilities import logger
from django.core.management.base import BaseCommand, CommandError

# Writing custom django-admin commands
# https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/

# Training.status:
STATUS_CREATED = 'Created'
STATUS_PROCESSING = 'Processing'
STATUS_COMPLETED = 'Completed'
STATUS_FAILED = 'Failed'

class Command(BaseCommand):
    """ A django command used to run training jobs, either any pending ones or those specifically indicated """

    help = 'Run training jobs'

    running = True

    def trainJob(self, training_id=None):
        """ Runs given training job or first pending job """
        training = None
        try:
            if training_id:
                training = api.models.Training.objects.get(pk=training_id)
            else:
                # TODO find a job that's waiting
                return
        except Training.DoesNotExist:
            raise CommandError('Training "%s" does not exist' % training_id)

        try:
            # update current status so other trainers won't get this job
            logger.info('Trainer.trainJob - training_id: %s, started', training_id)
            training.status = STATUS_PROCESSING
            training.save()

            # create model, apply requested settings
            settings = training.settings
            project_id = settings['project_id']
            project, model = get_project_model(project_id)

            # train model with given settings
            model.settings = settings
            results = model.train(training.id)

            # save results, mark as done
            training.results = results
            training.status = STATUS_COMPLETED
            training.save()
            logger.info('Trainer.trainJob - training_id: %s, completed', training_id)

            # TODO notifications

        except Exception as exc:
            logger.error(exc)
            training.status = STATUS_FAILED
            training.save()
        return training


    def add_arguments(self, parser):
        parser.add_argument('training_id', nargs='*', type=str) # zero or more training_id


    def handle(self, *args, **options):
        """ Called when command is run will keep processing jobs """
        logger.info('Trainer')

        # first run any jobs that were specifically indicated in the command
        for training_id in options['training_id']:
            self.trainJob(training_id)

        # then just wait for any pending jobs
        while self.running:
            try:
                self.trainJob()
            except Exception as exc:
                logger.error(exc)
                time.sleep(20)
            time.sleep(5)
        logger.info('Trainer - bye')
