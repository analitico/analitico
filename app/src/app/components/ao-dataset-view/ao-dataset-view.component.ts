/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ComponentFactoryResolver } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { environment } from '../../../environments/environment';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';
import { AoPipelineViewComponent } from '../ao-pipeline-view/ao-pipeline-view.component';
import { AoRefreshable } from 'src/app/ao-refreshable';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    templateUrl: './ao-dataset-view.component.html',
    styleUrls: ['./ao-dataset-view.component.css']
})
export class AoDatasetViewComponent extends AoPipelineViewComponent implements OnInit, OnDestroy, AoRefreshable {

    uploadAssetUrl: string;
    isProcessing = false;
    assets: any;
    data: any;


    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected pluginsService: AoPluginsService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected itemService: AoItemService,
        protected router: Router) {
        super(route, apiClient, componentFactoryResolver, pluginsService, snackBar, itemService);
    }

    refresh() {
        super.refresh();
    }

    ngOnInit() {
        super.ngOnInit();
        // get the view of the anchor component
        this.viewContainerRef = this.aoAnchor.viewContainerRef;
    }


    onLoad() {
        super.onLoad();
        this.uploadAssetUrl = environment.apiUrl + '/datasets/' + this.item.id + '/assets';
        this.assets = this.item.attributes && this.item.attributes.assets;
        this.data = this.item.attributes && this.item.attributes.data &&
            this.item.attributes.data.length > 0 && this.item.attributes.data[0];
        if (this.data) {
            this.data.jsonUrl = this.itemUrl + '/data/json';
        }
    }

    // execute the process command on the dataset and refresh status when finished
    process() {
        if (this.isProcessing) {
            return;
        }
        this.isProcessing = true;
        this.saveItem()
            .then(() => {
                const that = this;
                this.apiClient.post('/datasets/' + this.item.id + '/data/process', {})
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

    assetUploaded = () => {
        // we need to reload the item because it has assets info attached
        this.loadItem()
            .then(() => {
                // now we process to get the source plugin (if discovered)
                this.process();
            });
    }

    // fake plugin list (should be retrieved using api)
    _getPlugins(): any {
        return new Promise(function (resolve, reject) {
            const plugins = [{
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.AugmentDatesDataframePlugin',
            }];
            resolve({
                data: plugins
            });
        });
    }

    // create a recipe using data of this dataset
    createRecipe() {
        if (this.item.attributes.data && this.item.attributes.data.length === 1 && this.item.attributes.data[0].schema) {
            const recipe = {
                attributes: {
                    'workspace_id': this.item.attributes.workspace_id,
                    'plugin': {
                        'type': 'analitico/plugin',
                        'name': 'analitico.plugin.RecipePipelinePlugin',
                        'plugins': [{
                            'type': 'analitico/plugin',
                            'name': 'analitico.plugin.DatasetSourcePlugin',
                            'source': {
                                'dataset_id': this.item.id,
                                'schema': this.item.attributes.data[0].schema
                            }
                        }]
                    }
                }

            };

            this.apiClient.post('/recipes', recipe)
                .then((response) => {
                    this.router.navigate(['/recipes/' + response.data.id]);
                });
        }
    }
}
