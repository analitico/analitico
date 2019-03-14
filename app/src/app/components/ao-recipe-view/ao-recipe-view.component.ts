/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ComponentFactoryResolver } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';
import { AoPipelineViewComponent } from '../ao-pipeline-view/ao-pipeline-view.component';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { MatTableDataSource } from '@angular/material';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoMessageBoxService } from 'src/app/services/ao-message-box/ao-message-box';

@Component({
    templateUrl: './ao-recipe-view.component.html',
    styleUrls: ['./ao-recipe-view.component.css']
})
export class AoRecipeViewComponent extends AoPipelineViewComponent implements OnInit, OnDestroy {

    isProcessing = false;
    models: any;
    endpoints: any;
    tableModels: any;
    activeTabIndex: any;
    tabRouteSubscription: any;
    datasets: any;
    selectedDataset: any;
    currentView: string;
    hasPipeline = false; // if the recipe already has a pipeline
    selectedModel: any;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected pluginsService: AoPluginsService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected itemService: AoItemService,
        protected router: Router,
        protected messageBox: AoMessageBoxService) {
        super(route, apiClient, componentFactoryResolver, pluginsService, snackBar, itemService);
    }

    ngOnInit() {
        super.ngOnInit();

    }

    ngOnDestroy() {
        super.ngOnDestroy();
        if (this.tabRouteSubscription) {
            this.tabRouteSubscription.unsubscribe();
        }
    }

    /**
     * override method
     */
    loadItem() {
        return this.itemService.getRecipeById(this.objectId)
            .then((recipe: any) => {
                this.item = recipe;
                this.hasPipeline = this.item.attributes && this.item.attributes.plugin && this.item.attributes.plugin.plugins &&
                    this.item.attributes.plugin.plugins.length > 1;
                this.title = (this.item.attributes && this.item.attributes.title) || this.item.id;
                this.description = this.item.description;
                this.models = recipe._aoprivate.models;
                this.endpoints = recipe._aoprivate.endpoints;
                if (this.endpoints && this.endpoints.length === 1) {
                    this.selectedModel = this.endpoints[0]._aoprivate.model;
                }
                this.onLoad();
            })
            .catch((response) => {
                if (response.status === 404) {
                    window.location.href = '/app';
                }
            });
    }

    onLoad() {
        super.onLoad();
        if (this.tabRouteSubscription) {
            this.tabRouteSubscription.unsubscribe();
        }
        this.tabRouteSubscription = this.route.queryParams.subscribe(this.checkRouteForTab.bind(this));

        if (this.models) {
            // assign data source for the table
            this.tableModels = new MatTableDataSource(this.models);
        }

        this.loadDatasets();
    }


    // update selected tab according to view parameters
    // redirect to live view if there is an endpoint
    // redirect to recipe view if no endpoints
    checkRouteForTab(params: any) {
        this.currentView = params.view;
        if (!this.currentView && this.endpoints && this.endpoints.length > 0) {
            return this.router.navigate([], { queryParams: { view: 'live' }, relativeTo: this.route, replaceUrl: true });
        }

        if (this.currentView === 'live' && (!this.endpoints || this.endpoints.length === 0)) {
            return this.router.navigate([], { queryParams: { view: 'recipe' }, relativeTo: this.route, replaceUrl: true });
        }
        if (this.currentView === 'live') {
            this.activeTabIndex = 2;
        } else if (this.currentView === 'models') {
            this.activeTabIndex = 1;
        } else {
            this.activeTabIndex = 0;
        }
    }

    // change view parameters when tab is selected
    selectedTabChanged(tabIndex) {
        if (tabIndex === 0) {
            this.router.navigate([], { queryParams: { view: 'recipe' }, relativeTo: this.route });
        } else if (tabIndex === 1) {
            this.router.navigate([], { queryParams: { view: 'models' }, relativeTo: this.route });
        } else if (tabIndex === 2) {
            this.router.navigate([], { queryParams: { view: 'live' }, relativeTo: this.route });

        }
    }
    // returns the dataset associated with the recipe (if any)
    getRecipeDatasetId() {
        try {
            return this.item.attributes['plugin'].plugins[0].source.dataset_id;
        } catch (e) {
            return false;
        }
    }

    // load datasets that can be associated with this recipe
    loadDatasets() {
        this.itemService.getDatasets()
            .then((datasets) => {
                // filter datasets according to recipe workspace
                this.datasets = this.itemService.filterItemsByDictionary(datasets,
                    { 'attributes.workspace_id': this.item.attributes.workspace_id });
                // select dataset
                const datasetId = this.getRecipeDatasetId();
                this.selectedDataset = this.itemService.getItemById(datasets, datasetId);

            });
    }

    // train the recipe
    train() {
        if (this.isProcessing) {
            return;
        }
        this.isProcessing = true;
        this.saveItem()
            .then(() => {
                const that = this;
                this.apiClient.post('/recipes/' + this.item.id + '/jobs/train', {})
                    .then((response: any) => {
                        const jobId = response.data.id;
                        // set a watcher for this job
                        this.jobService.watchJob(jobId)
                            .subscribe({
                                next(data: any) {
                                    if (data.status !== 'processing') {
                                        that.isProcessing = false;
                                        // reload
                                        that.loadItem();
                                    }
                                }
                            });
                    })
                    .catch(() => {
                        this.isProcessing = false;
                    });
            })
            .catch(() => {
                this.isProcessing = false;
            });
    }

    // fake plugin list (should be retrieved using api)
    _getPlugins(): any {
        return new Promise(function (resolve, reject) {
            const plugins = [{
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.CatBoostRegressorPlugin',
                'parameters': {
                    'iterations': 50,
                    'learning_rate': 1,
                    'depth0': 8
                },
                'data': {
                    'label': ''
                }
            },
            {
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.CatBoostClassifierPlugin',
                'parameters': {
                    'iterations': 50,
                    'learning_rate': 1,
                    'depth0': 8
                },
                'data': {
                    'label': ''
                }
            }

            ];
            resolve({
                data: plugins
            });
        });
    }

    // create a new end point for a given model
    createEndpointForModel(model) {
        this.itemService.createEndpointForModel(model)
            .then((endpoint) => {
                // open the endpoint page
                // this.router.navigate(['/endpoints/' + endpoint.id]);
                this.activeTabIndex = 2;
            });

    }

    // ask to change the model associated with this endpoint
    requestToSetNewModel(model) {
        const subscription =
            this.messageBox.show('Do you want to change the model associated with this endpoint?',
                'Changing endpoint model', 'WARNING: this could affect your production data', 2)
                .subscribe((response) => {
                    subscription.unsubscribe();
                    if (response.result === 'yes') {
                        this.setModel(model);
                    }
                });
    }

    // sets the model_id of the first endpoint and reloads item
    setModel(model) {
        if (this.endpoints.length === 0) {
            this.createEndpointForModel(model);
        } else if (this.endpoints.length === 1) {
            // change the first endpoint
            return this.itemService.changeEndpointModel(this.endpoints[0], model.id)
                .then(() => {
                    this.loadItem();
                });
        }
    }

    // change the dataset in the recipe
    changedDataset() {
        this.setRecipeDataset(this.selectedDataset.id);
    }

    setRecipeDataset(datasetId) {
        if (!this.item.attributes.plugin) {
            this.item.attributes['plugin'] = {
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.RecipePipelinePlugin',
                'plugins': []
            };
        }
        // add datasource with the selected dataset
        this.item.attributes['plugin'].plugins[0] = {
            'type': 'analitico/plugin',
            'name': 'analitico.plugin.DatasetSourcePlugin',
            'source': {
                'dataset_id': datasetId
            }
        };

        return this.saveItem();
    }

    // create a new dataset and return asset upload url
    getNewDatasetUploadUrl = (file) => {
        // create dataset
        return this.apiClient.post('/datasets', { workspace_id: this.item.attributes.workspace_id })
            .then((response: any) => {
                return { file: file, url: '/api/datasets/' + response.data.id + '/assets' };
            });
    }

    // open dataset view for the uploaded dataset
    afterNewDatasetUploaded = (fileItem) => {
        if (fileItem.uploadUrl) {
            const datasetId = (fileItem.uploadUrl.substring(
                fileItem.uploadUrl.indexOf('/datasets/') + 10).replace('/assets', ''));

            this.setRecipeDataset(datasetId);
            // process dataset
            const that = this;
            return this.itemService.processDataset(datasetId)
                .catch(() => {

                });

        }
    }

}
