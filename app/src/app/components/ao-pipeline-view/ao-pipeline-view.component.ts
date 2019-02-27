import { Component, OnInit, OnDestroy, AfterViewInit, ViewContainerRef, ViewChild, ComponentFactoryResolver } from '@angular/core';
import { AoViewComponent } from '../ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { MatSnackBar } from '@angular/material';

@Component({
    selector: 'app-ao-pipeline-view',
    templateUrl: './ao-pipeline-view.component.html',
    styleUrls: ['./ao-pipeline-view.component.css']
})

export class AoPipelineViewComponent extends AoViewComponent implements OnInit, OnDestroy, AfterViewInit {
    // this is the object where we will insert the child components
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;
    newDataSubscriptions: any;
    plugins: any;
    viewContainerRef: ViewContainerRef;
    title: string;
    pluginData: any;
    saveTimeout: any;

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected pluginsService: AoPluginsService,
        protected snackBar: MatSnackBar) {
        super(route, apiClient);
    }

    ngOnInit() {
        super.ngOnInit();
        this.newDataSubscriptions = [];
        this.loadPlugins();
    }

    ngOnDestroy() {
        super.ngOnDestroy();
        console.log('destroyed ' + this.item.id);
    }

    ngAfterViewInit() {
        // get the view of the anchor component
        this.viewContainerRef = this.aoAnchor.viewContainerRef;
        this.checkIfCanBeLoaded();
    }

    onLoad() {
        this.checkIfCanBeLoaded();
    }

    // syncronizing data load (onLoad) and viewContainerRef that is set only AfterViewInit
    checkIfCanBeLoaded() {
        if (this.item && this.item.id && this.viewContainerRef) {
            // clear the view
            this.viewContainerRef.clear();
            this.title = (this.item.attributes && this.item.attributes.title) || this.item.id;

            this.pluginData = null;
            // unsubscribe to data notifications of previous item
            this.newDataSubscriptions.forEach((sub: any) => {
                sub.unsubscribe();
            });
            this.newDataSubscriptions = [];
            // load plugin
            this.loadPlugin();
        }
    }

    hasPlugin(): boolean {
        return typeof this.item.attributes.plugin !== 'undefined' && this.item.attributes.plugin;
    }

    // load the plugin
    loadPlugin() {
        if (this.hasPlugin()) {
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
                // subscribe to updates from subcomponents
                const sub = instance.onNewDataSubject.subscribe(this.onNewDataFromPlugin.bind(this));
                // store subscriptions
                this.newDataSubscriptions.push(sub);
            }
        }
    }

    // called when the model is changed by plugins
    onNewDataFromPlugin(): void {
        // we want to wait a bit before saving
        // this.checkIfNeedToSave();
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

    _getPlugins(): any {
        return new Promise((resolve, reject) => {
            resolve([]);
        });
    }

    // load plugin list
    loadPlugins() {
        this._getPlugins()
            .then((response) => {
                this.plugins = response.data;
            });
    }


    save() {
        this.saveItem();
    }
}
