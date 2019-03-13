/**
 * Basic operations with items: load, save etc...
 */
import { Injectable } from '@angular/core';
import { AoApiClientService } from '../ao-api-client/ao-api-client.service';
import * as _ from 'lodash';
import { AoJobService } from '../ao-job/ao-job.service';

@Injectable({
    providedIn: 'root'
})
export class AoItemService {

    constructor(protected apiClient: AoApiClientService, protected jobService: AoJobService) { }

    // loads the json object
    loadItem(item, url?) {
        // if not url
        if (!url) {
            // get from item links
            url = item.links.self;
        }
        return this.apiClient.get(url)
            .then((response: any) => {
                return response.data;
            });
    }

    saveItem(item) {
        // remove the _aoprivate key which is used by app but does not have to be stored
        delete item._aoprivate;
        const url = item.links.self;
        return this.apiClient.patch(url, item)
            .then((response: any) => {
                return response.data;
            });
    }

    /**
     * Find if it can find a property with the required value (substring)
     * @param obj dictionary
     * @param filterString string to find
     */
    hasValueInProperty(obj, filterString) {
        if (typeof obj === 'object') {
            for (const key in obj) {
                // do not look into _aoprivate to avoid infinite loop
                if (key === '_aoprivate') {
                    continue;
                }
                // optional check for properties from prototype chain
                if (obj.hasOwnProperty(key)) {
                    const value = obj[key];

                    if (this.hasValueInProperty(value, filterString)) {
                        return true;
                    }

                }
            }
        } else if (Array.isArray(obj)) {
            for (let i = 0; i < obj.length; i++) {
                if (this.hasValueInProperty(obj[i], filterString)) {
                    return true;
                }
            }
        } else {
            try {
                if (('' + obj).toLowerCase().indexOf(filterString.toLowerCase()) >= 0) {
                    return true;
                }
            } catch (e) {
                console.error(e);
            }
        }

    }

    /**
     * Filter a collection of items by property values
     * @param items collection
     * @param filterString string to find in collection properties values
     */
    filterItemsByString(items, filterString) {
        const filtered = [];
        items.forEach(item => {
            if (this.hasValueInProperty(item, filterString.toLowerCase())) {
                filtered.push(item);
            }
        });
        return filtered;
    }


    /**
     * Filter a collection using a dictionary
     * @param items collection
     * @param filter dictionary of properties (path are supported) and required values
     */
    filterItemsByDictionary(items, filter): any {
        return items.filter((item) => {
            for (const filterKey in filter) {
                if (filter.hasOwnProperty(filterKey)) {
                    // get the value specified in the filter path
                    const value = _.get(item, filterKey);
                    const filterValue = filter[filterKey];
                    // compare object value with filter value
                    if (value !== filterValue) {
                        return false;
                    }
                }
            }
            return true;
        });
    }

    /**
     * Get algorithm used by model
     * @param model model
     */
    getModelAlgorithm(model) {
        try {
            return model.attributes.training.algorithm;
        } catch (e) {
            return null;
        }
    }

    /**
     * Get KPI values of model
     * @param model model
     */
    getModelKPIValues(model) {
        const algo = this.getModelAlgorithm(model);
        // "algorithm": "ml/binary-classification"
        const kpi = [];
        try {
            switch (algo) {
                case 'ml/binary-classification':
                    kpi.push({
                        name: 'Log loss',
                        value: model.attributes.training.scores.log_loss
                    });
                    break;
                default:
                    kpi.push({
                        name: 'Test',
                        value: 'test'
                    });
                    break;
            }
        } catch (e) {
        }
        return kpi;

    }

    /**
     * Returns the item with a given id
     * @param items array of items
     * @param id required id
     */
    getItemById(items, id) {
        for (let i = 0, l = items.length; i < l; i++) {
            if (items[i].id === id) {
                return items[i];
            }
        }
        return null;
    }

    /**
     * Filter a list of items using an Attibute,Value filter
     * @param items array of items
     * @param attribute attribute path
     * @param value attribute value
     */
    getItemsByAttribute(items, attribute, value) {
        const filteredItems = [];
        for (let i = 0, l = items.length; i < l; i++) {
            if (_.get(items[i], attribute) === value) {
                filteredItems.push(items[i]);
            }
        }
        return filteredItems;
    }

    /**
     * Return the list of all item available to the user with their relationships
     */
    getItems() {
        let datasets = null;
        let models = null;
        let endpoints = null;
        let recipes = null;
        return Promise.all([
            this.apiClient.get('/datasets')
                .then((response) => {
                    datasets = response.data;
                }),
            this.apiClient.get('/models')
                .then((response) => {
                    models = response.data;
                }),
            this.apiClient.get('/endpoints')
                .then((response) => {
                    endpoints = response.data;
                }),
            this.apiClient.get('/recipes')
                .then((response) => {
                    recipes = response.data;
                })
        ])
            .then(() => {
                datasets.forEach(dataset => {
                    // get model recipe and endpoints
                    dataset._aoprivate = {
                        recipes: this.getItemsByAttribute(recipes, 'attributes.plugin.plugins[0].source.dataset_id', dataset.id)
                    };
                });

                models.forEach(model => {
                    // get model recipe and endpoints
                    model._aoprivate = {
                        recipe: this.getItemById(recipes, model.attributes.recipe_id),
                        endpoints: this.getItemsByAttribute(endpoints, 'attributes.model_id', model.id)
                    };
                    model = this.augmentModels(model);
                });

                recipes.forEach(recipe => {
                    // get recipe models
                    recipe._aoprivate = {
                        models: this.getItemsByAttribute(models, 'attributes.recipe_id', recipe.id),
                        endpoints: []
                    };

                    // how find if recipe is related to endpoint
                    recipe._aoprivate.models.forEach(model => {
                        if (model._aoprivate.endpoints) {
                            recipe._aoprivate.endpoints = recipe._aoprivate.endpoints.concat(model._aoprivate.endpoints);
                        }
                    });

                });

                endpoints.forEach(endpoint => {
                    // get endpoint model
                    endpoint._aoprivate = {
                        model: this.getItemById(models, endpoint.attributes.model_id)
                    };

                });
                const result = { datasets: datasets, models: models, recipes: recipes, endpoints: endpoints };
                console.log(result);
                return result;
            });
    }

    /**
     * Augment the models with additional data
     * @param models array of models
     */
    augmentModels(models) {
        if (Array.isArray(models)) {
            for (let i = 0, l = models.length; i < l; i++) {
                models[i] = this.augmentModels(models[i]);
            }
            return models;
        } else {
            const model = models;
            // create private dictionary if it not exists
            if (!model._aoprivate) {
                model._aoprivate = {};
            }
            model._aoprivate['kpi'] = this.getModelKPIValues(model);
            return model;
        }
    }


    /**
     * Get datasets
     */
    getDatasets() {
        return this.getItems()
            .then((items) => {
                return items.datasets.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }


    /**
     * Get models
     */
    getModels() {
        return this.getItems()
            .then((items) => {
                return items.models.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }

    /**
     * Get recipes
     */
    getRecipes() {
        return this.getItems()
            .then((items) => {
                return items.recipes.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }
    /**
     * Get endpoints
     */
    getEndpoints() {
        return this.getItems()
            .then((items) => {
                return items.endpoints.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }

    /**
     * Get the model with the provided id
     * @param id require id
     */
    getModelById(id) {
        return this.getModels()
            .then((models) => {
                return this.getItemById(models, id);
            });
    }

    /**
     * Get the recipe with the provided id
     * @param id require id
     */
    getRecipeById(id) {
        return this.getRecipes()
            .then((recipes) => {
                return this.getItemById(recipes, id);
            });
    }

    /**
     * Create a new endpoint for this model
     * @param model the model
     */
    createEndpointForModel(model) {

        const params = { attributes: { 'workspace_id': model.attributes.workspace_id, model_id: model.id } };
        return this.apiClient.post('/endpoints', params)
            .then((response) => {
                return response.data;
            });

    }

    /**
     * Process a dataset and returns a Subject that will emit processing progress
     * @param datasetId dataset id
     */
    processDataset(datasetId) {
        return this.apiClient.post('/datasets/' + datasetId + '/data/process', {})
            .then((response: any) => {
                const jobId = response.data.id;
                // set a watcher for this job
                return this.jobService.watchJob(jobId);
            });
    }

    /**
     * Change the model associated with an endpoint.
     * It will also reset the endpoint pipeline removing the attributes.plugin fiels
     * The pipeline will be rebuilt using the model
     * @param endpoint the endpoint object
     * @param modelId new model id
     */
    changeEndpointModel(endpoint, modelId) {
        endpoint.attributes.model_id = modelId;
        // remove old pipeline
        delete endpoint.attributes.plugin;
        return this.saveItem(endpoint);
    }
}
