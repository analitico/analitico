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

@Component({
    templateUrl: './ao-dataset-view.component.html',
    styleUrls: ['./ao-dataset-view.component.css']
})
export class AoDatasetViewComponent extends AoViewComponent implements OnInit {
    // this is the object where we will insert the child components
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;

    title: string;
    viewContainerRef: ViewContainerRef;
    private pluginData: any;
    private saveTimeout: any;
    assetsUrl: string;


    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        private componentFactoryResolver: ComponentFactoryResolver,
        private pluginsService: AoPluginsService,
        private snackBar: MatSnackBar) {
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
        this.assetsUrl = '/datasets/' + this.item.id + '/assets';
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
}
