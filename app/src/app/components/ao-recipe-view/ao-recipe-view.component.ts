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

@Component({
    templateUrl: './ao-recipe-view.component.html',
    styleUrls: ['./ao-recipe-view.component.css']
})
export class AoRecipeViewComponent extends AoPipelineViewComponent implements OnInit, OnDestroy {

    isProcessing = false;
    models: any;
    tableModels: any;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected pluginsService: AoPluginsService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected itemService: AoItemService,
        protected router: Router) {
        super(route, apiClient, componentFactoryResolver, pluginsService, snackBar, itemService);
    }

    ngOnInit() {
        super.ngOnInit();

    }

    onLoad() {
        super.onLoad();
        this.loadModels();
    }

    loadModels() {
        this.itemService.getModels()
            .then((models: any) => {
                this.models = [];
                models.forEach(model => {
                    if (model.attributes.recipe_id === this.item.id) {
                        this.models.push(model);
                    }
                });
                // sort updated_at desc
                this.models.sort(function (a, b) {
                    return a.attributes.updated_at > b.attributes.updated_at ? -1 : 1;
                });
                // assign data source for the table
                this.tableModels = new MatTableDataSource(this.models);
            });
    }

    train() {
        if (this.isProcessing) {
            return;
        }
        this.isProcessing = true;
        this.saveItem()
            .then(() => {
                const that = this;
                this.apiClient.post('/recipes/' + this.item.id + '/train', {})
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

    createEndpointForModel(model) {
        this.itemService.createEndpointForModel(model)
            .then((endpoint) => {
                // open the endpoint page
                this.router.navigate(['/endpoints/' + endpoint.id]);
            });

    }

}
