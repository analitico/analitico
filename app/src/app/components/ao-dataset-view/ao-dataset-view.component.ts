/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ViewChild, ComponentFactoryResolver, ViewContainerRef } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { MatSnackBar } from '@angular/material/snack-bar';
import { environment } from '../../../environments/environment';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';

@Component({
    templateUrl: './ao-dataset-view.component.html',
    styleUrls: ['./ao-dataset-view.component.css']
})
export class AoDatasetViewComponent extends AoViewComponent implements OnInit {
    // this is the object where we will insert the child components
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;

    title: string;
    viewContainerRef: ViewContainerRef;
    pluginData: any;
    saveTimeout: any;
    uploadAssetUrl: string;
    isProcessing = false;
    assets: any;
    data: any;
    // if the dataset has only one data it is a table
    outputTableSchema: any;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        private componentFactoryResolver: ComponentFactoryResolver,
        private pluginsService: AoPluginsService,
        private snackBar: MatSnackBar,
        private jobService: AoJobService) {
        super(route, apiClient);
    }
    static hasPlugin(item): boolean {
        return typeof item.attributes.plugin !== 'undefined' && item.attributes.plugin;
    }
    ngOnInit() {
        super.ngOnInit();
        // get the view of the anchor component
        this.viewContainerRef = this.aoAnchor.viewContainerRef;
    }

    onLoad() {
        console.log('onLoad');
        this.uploadAssetUrl = environment.apiUrl + '/datasets/' + this.item.id + '/assets';
        // clear the view
        this.viewContainerRef.clear();

        this.title = (this.item.attributes && this.item.attributes.title) || this.item.id;

        // create plugin if it does not exist
        /* if (!AoDatasetViewComponent.hasPlugin(this.item)) {
            // add Pipeline plugin
            this.item.attributes.plugin = {
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.PipelinePlugin',
                'plugins': []
            };
            // save
            return this.saveItem()
                .then(() => {
                    this.onLoad();
                });
        } */
        this.assets = this.item.attributes && this.item.attributes.assets;
        this.data = this.item.attributes && this.item.attributes.data;
        // if only one data, consider its schema as the table schema
        if (this.data.length === 1 && this.data[0].schema) {
            this.outputTableSchema = this.data[0].schema;
        }
        this.loadPlugin();
    }

    // load the plugin
    loadPlugin() {
        if (AoDatasetViewComponent.hasPlugin(this.item)) {
            // if we have a plugin
            this.pluginData = this.item.attributes.plugin;
            // find the class name of the plugin
            const pluginName = this.pluginData.name.split('.')[2];
            // get the plugin component
            const plugin = this.pluginsService.getPlugin(pluginName);
            // if we have found the plugin...
            if (plugin) {
                // get the plugin component factory
                const componentFactory = this.componentFactoryResolver.resolveComponentFactory(plugin);
                // add the component to the anchor view
                const componentRef = this.viewContainerRef.createComponent(componentFactory);
                (<IAoPluginInstance>componentRef.instance).pluginsService = this.pluginsService;
                // get data subject
                const instance = (<IAoPluginInstance>componentRef.instance);
                // send data
                instance.setData(this.pluginData);
                // subscribe to update
                instance.onNewDataSubject.subscribe(this.onNewData.bind(this));
            }
        }
    }

    // called when the model is changed
    onNewData(): void {
        // we want to wait a bit before saving
        this.checkIfNeedToSave();
    }
    // wait a bit before automatically saving changes to object
    checkIfNeedToSave() {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.saveTimeout = setTimeout(this.saveItem.bind(this), 3000);
    }

    onSaved() {
        // show a message
        this.snackBar.open('Item has been saved', null, { duration: 3000 });
    }

    // execute the process command on the dataset and refresh status when finished
    process() {
        const that = this;
        this.isProcessing = true;
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
            });
    }

    assetUploaded() {
        // this.process();
    }
}
