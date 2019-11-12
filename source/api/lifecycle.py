import django.db.models.signals
import api.models

from analitico import logger
from api.models.drive import dr_delete_workspace_storage
from api.k8 import k8_jupyter_deallocate
from django.dispatch import receiver

# Django signals:
# https://docs.djangoproject.com/en/2.2/topics/signals/

# Delete signals from Django models:
# https://docs.djangoproject.com/en/dev/ref/signals/#post-delete


##
## Deletion of item's files in storage
##


def post_delete_item_storage(item):
    """
    Delete files in storage associated with this item.
    
    Arguments:
        item {Dataset, Recipe, Notebook, Model} -- The item to be deleted.
    """
    try:
        if isinstance(item, api.models.ItemMixin):
            storage = item.storage
            if storage:
                driver = storage.driver
                assert isinstance(driver, api.libcloud.WebdavStorageDriver)

                if isinstance(item, api.models.Workspace):
                    storage_conf = item.get_attribute("storage")
                    if storage_conf["driver"] == "hetzner-webdav":
                        # when a workspace is deleted we can deallocate the subuser which is allocated on the
                        # storage box and all the files that is contains. some development accounts can be kept
                        # without recreating the subaccount every time (eg. when unit testing) so they are marked
                        # with a "hold" property.
                        hold = storage_conf.get("hold", False)
                        if not hold:
                            dr_delete_workspace_storage(item)
                            logger.info(f"Deleted storage account for {item.id}")
                else:
                    # regular item, delete files
                    item_path = item.storage_base_path
                    if driver.exists(item_path):
                        driver.rmdir(item_path)
                        logger.info(f"Deleted files for {item.id}: {item_path}")
    except Exception as exc:
        logger.error(f"post_delete_item_storage - item: {item.id}, failed: {exc}")
        raise exc


##
## Signals used to receive notifications when models are deleted and cleanup resources
##


@receiver(django.db.models.signals.post_delete, sender=api.models.Dataset)
def post_delete_dataset(sender, instance, *args, **kwargs):
    post_delete_item_storage(instance)


@receiver(django.db.models.signals.post_delete, sender=api.models.Recipe)
def post_delete_recipe(sender, instance, *args, **kwargs):
    post_delete_item_storage(instance)


@receiver(django.db.models.signals.post_delete, sender=api.models.Notebook)
def post_delete_notebook(sender, instance, *args, **kwargs):
    post_delete_item_storage(instance)


@receiver(django.db.models.signals.post_delete, sender=api.models.Model)
def post_delete_model(sender, instance, *args, **kwargs):
    post_delete_item_storage(instance)


@receiver(django.db.models.signals.post_delete, sender=api.models.Workspace)
def post_delete_workspace(sender, instance, *args, **kwargs):
    post_delete_item_storage(instance)
    k8_jupyter_deallocate(instance)
