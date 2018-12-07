
import os
import time

from api.models import Training
from api.views import get_project_model
from analitico.utilities import logger

from django.core.management.base import BaseCommand, CommandError

# Writing custom django-admin commands
# https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/

class Command(BaseCommand):
    """ A django command used to run training jobs, either any pending ones or those specifically indicated """

    help = 'Run training jobs'

    running = True

    def trainJob(self, training_id=None):
        """ Runs given training job or first pending job """
        training = None
        try:
            if training_id:
                training = Training.objects.get(pk=training_id)
            else:
                pending = Training.objects.filter(status=Training.STATUS_CREATED)
                if pending.count() < 1:
                    logger.info('Trainer.trainJob - no pending jobs')
                    return
                training = pending[0]
        except Training.DoesNotExist:
            raise CommandError('Training "%s" does not exist' % training_id)

        try:
            # update current status so other trainers won't get this job
            logger.info('Trainer.trainJob - training_id: %s, started', training_id)
            training.status = Training.STATUS_PROCESSING
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
            training.status = Training.STATUS_COMPLETED
            training.save()
            logger.info('Trainer.trainJob - training_id: %s, completed', training_id)

            # TODO notifications

        except Exception as exc:
            logger.error(exc)
            training.status = Training.STATUS_FAILED
            training.save()
        return training


    def add_arguments(self, parser):
        parser.add_argument('training_id', nargs='*', type=str) # zero or more training_id


    def handle(self, *args, **options):
        """ Called when command is run will keep processing jobs """
        logger.info('Trainer - started')

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
