from django.urls import reverse
from rest_framework import status


from api.models import *
from .utils import AnaliticoApiTestCase


class AutomlTests(AnaliticoApiTestCase):

    def test_automl_run(self):
        # create a recipe with automl configs
        recipe = Recipe.objects.create(pk="rx_iris", workspace_id=self.ws1.id)
        recipe.set_attribute(
            "automl",
            {
                "workspace_id": "ws_automl",
                "recipe_id": "rx_iris",
                "data_item_id": "rx_iris",
                "data_path": "data",
                "prediction_type": "regression",
                "target_column": "target",
            },
        )
        recipe.save()
        # upload dataset used by pipeline
        self.auth_token(self.token1)
        data_url = url = reverse("api:recipe-files", args=(recipe.id, "data/iris.csv"))
        self.upload_file(
            data_url,
            "../../../../automl/mount/recipes/rx_iris/data/iris.csv",
            content_type="text/csv",
            token=self.token1,
        )

        # user cannot run automl he doesn't have access to
        self.auth_token(self.token2)
        url = reverse("api:recipe-automl-run", args=(recipe.id,))
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # without automl_config
        self.auth_token(self.token2)
        recipe_without_automl_config = Recipe.objects.create(pk="rx_without_automl_config", workspace_id=self.ws2.id)
        url = reverse("api:recipe-automl-run", args=(recipe_without_automl_config.id,))
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # user can run an automl config on its recipe
        # request to run the pipeline
        self.auth_token(self.token1)
        url = reverse("api:recipe-automl-run", args=(recipe.id,))
        response = self.client.post(url)
        self.assertApiResponse(response)

        data = response.json().get("data")
        attributes = data["attributes"]

        # not yet started
        self.assertIn("automl", attributes)
        self.assertIsNotNone(attributes["automl"])
        # run id is saved in automl config
        recipe.refresh_from_db()
        self.assertEqual(attributes["automl"]["run_id"], recipe.get_attribute("automl.run_id"))

