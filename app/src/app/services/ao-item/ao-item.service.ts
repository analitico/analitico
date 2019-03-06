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

    getItemById(items, id) {
        for (let i = 0, l = items.length; i < l; i++) {
            if (items[i].id === id) {
                return items[i];
            }
        }
        return null;
    }

    getItemsByAttribute(items, attribute, value) {
        const filteredItems = [];
        for (let i = 0, l = items.length; i < l; i++) {
            if (_.get(items[i], attribute) === value) {
                filteredItems.push(items[i]);
            }
        }
        return filteredItems;
    }

    getItems() {
        let models = null;
        let endpoints = null;
        let recipes = null;
        return Promise.all([
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
                return { models: models, recipes: recipes, endpoints: endpoints };
            });
    }

    augmentModels(models) {
        if (Array.isArray(models)) {
            for (let i = 0, l = models.length; i < l; i++) {
                models[i] = this.augmentModels(models[i]);
            }
            return models;
        } else {
            const model = models;
            if (!model._aoprivate) {
                model._aoprivate = {};
            }
            model._aoprivate['kpi'] = this.getModelKPIValues(model);
            return model;
        }
    }

    /**
     * Get models width kpi, recipe and endpoints
     */
    getModels() {
        return this.getItems()
            .then((items) => {
                items.models.forEach(model => {
                    model._aoprivate = {
                        recipe: this.getItemById(items.recipes, model.attributes.recipe_id),
                        endpoints: this.getItemsByAttribute(items.endpoints, 'attributes.model_id', model.id)
                    };
                    model = this.augmentModels(model);

                });
                return items.models.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }

    getRecipes() {
        return this.getItems()
            .then((items) => {
                items.recipes.forEach(recipe => {
                    // get recipe models
                    recipe._aoprivate = {
                        models: this.augmentModels(this.getItemsByAttribute(items.models, 'attributes.recipe_id', recipe.id))
                    };

                });
                return items.recipes.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }

    getEndpoints() {
        return this.getItems()
            .then((items) => {
                items.endpoints.forEach(endpoint => {
                    // look for endpoint model
                    endpoint._aoprivate = {
                        model: this.augmentModels(this.getItemById(items.models, endpoint.attributes.model_id))
                    };

                });
                return items.endpoints.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
            });
    }


    getModelById(id) {
        return this.getModels()
            .then((models) => {
                return this.getItemById(models, id);
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

    processDataset(datasetId) {
        return this.apiClient.post('/datasets/' + datasetId + '/data/process', {})
            .then((response: any) => {
                const jobId = response.data.id;
                // set a watcher for this job
                return this.jobService.watchJob(jobId);
            });
    }
}
