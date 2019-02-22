/**
    A plugin that creates a linear workflow by chaining together other plugins.
    Plugins that are chained in a pipeline need to take a single input and have
    a single output of the same kind so they same object can be processed from
    the first, to the next and down to the last, then returned to caller as if
    the process was just one logical operation. PipelinePlugin can be used to
    for example to construct ETL (extract, transform, load) workflows.
 */

import { Component, OnInit, ViewChildren, ComponentFactoryResolver, ViewContainerRef, QueryList, AfterViewInit } from '@angular/core';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';

@Component({
    selector: 'app-ao-pipeline-plugin',
    templateUrl: './ao-pipeline-plugin.component.html',
    styleUrls: ['./ao-pipeline-plugin.component.css']
})
export class AoPipelinePluginComponent extends AoPluginComponent implements AfterViewInit {
    // list of plugins of the pipeline
    plugins: any;
    // reference to plugins service
    pluginsService: any;
    // references to plugin components
    pluginInstances: any = [];
    // DOM boxes to render plugins
    pluginElements: any = [];
    // we have subscribed to received updates when plugins dom elements are created
    pluginViewsSubscription: any;

    movingPluginPreviousIndex: any;

    // this is the object where we will insert the child components
    @ViewChildren(AoAnchorDirective) pluginViews: QueryList<any>;
    constructor(private componentFactoryResolver: ComponentFactoryResolver) {
        super();

    }
    // wait to receive reference to pluginViews
    ngAfterViewInit() {
        // subscribe to changes on AoAnchorDirective views
        this.pluginViewsSubscription = this.pluginViews.changes.subscribe(this.onPluginViewChanges.bind(this));
        // ready to create views
        setTimeout(this.createPluginElements.bind(this), 1);
    }

    // views are created
    onPluginViewChanges(views: any) {
        this.pluginViewsSubscription.unsubscribe();
        // async to avoid errors
        setTimeout(this.loadPlugins.bind(this), 1);
    }
    // create empty boxes for plugins
    createPluginElements() {
        if (this.pluginViewsSubscription && this.data) {
            // create elements for plugins
            if (this.data && this.data.plugins) {
                this.plugins = this.data.plugins;
            }
        }
    }

    setData(data: any) {
        super.setData(data);
        // if it contains plugins -> load them
        this.createPluginElements();
    }

    // loads all the plugins
    loadPlugins(): void {
        const views = this.pluginViews.toArray();
        this.plugins.forEach((pluginData, index) => {
            const viewContainerRef = views[index].viewContainerRef;
            viewContainerRef.clear();
            this.loadPlugin(pluginData, viewContainerRef);
        });
    }

    // load the plugin
    loadPlugin(pluginData: any, viewContainerRef: ViewContainerRef): void {
        // find the class name of the plugin
        const pluginName = pluginData.name.split('.')[2];
        // get the plugin component
        const plugin = this.pluginsService.getPlugin(pluginName);
        if (plugin) {
            // get the plugin component factory
            const componentFactory = this.componentFactoryResolver.resolveComponentFactory(plugin);
            // add the component to the anchor view
            const componentRef = viewContainerRef.createComponent(componentFactory);
            const instance = (<IAoPluginInstance>componentRef.instance);
            this.pluginInstances.push(instance);
            // set data to the plugin
            instance.setData(pluginData);
            // subscribe to update
            instance.onNewDataSubject.subscribe(this.onNewDataFromPlugin.bind(this));
        } else {
            throw new Error('Missing plugin, cannot build pipeline');
        }
    }

    // when we receive data change notifications we want to update the correspondent data model and pass
    // the notification above
    onNewDataFromPlugin(): void {
        // notify upper levels
        this.onNewDataSubject.next();
    }
    // these methods will be overwritten in subclasses
    canPluginBeMoved(pluginPreviousIndex, pluginCurrentIndex): boolean { return true; }
    canPluginBeAdded(plugin, pluginCurrentIndex): boolean { return true; }

    createNewPlugin(event) {
        const plugin = event.previousContainer.data[event.previousIndex];
        const pluginCurrentIndex = event.currentIndex;
        if (this.canPluginBeAdded(plugin, pluginCurrentIndex)) {
            // add object into plugin list
            this.plugins.splice(pluginCurrentIndex, 0, plugin);
            // load the plugin
            setTimeout(this.loadPlugins.bind(this));
        }
    }

    // change a plugin position
    movePlugin(previousIndex, currentIndex) {
        // check if move is ok
        if (this.canPluginBeMoved(previousIndex, currentIndex)) {
            // move plugin
            moveItemInArray(this.plugins, previousIndex, currentIndex);
            // notify upper levels (i.e. save)
            this.onNewDataSubject.next();
        }
    }

    // handle drop event in plugin list
    drop(event: CdkDragDrop<string[]>) {
        if (event.previousContainer !== event.container) {
            // this is coming from outsite: we are adding a new plugin to the pipeline
            return this.createNewPlugin(event);
        }
        if (this.movingPluginPreviousIndex) {
            const movingPlugin = this.plugins[this.movingPluginPreviousIndex];
            delete movingPlugin.notValidPosition;
            // reset the reference to the moving plugin
            this.movingPluginPreviousIndex = null;
        }
        // try to move the plugin
        this.movePlugin(event.previousIndex, event.currentIndex);
    }

    // called while dragging the plugin in the pipeline,
    // should give warnings to users about invalid plugin positions
    sorting(event) {
        if (!this.movingPluginPreviousIndex) {
            this.movingPluginPreviousIndex = event.previousIndex;
        }
        // check if move is ok
        const movingPlugin = this.plugins[this.movingPluginPreviousIndex];
        if (!this.canPluginBeMoved(this.movingPluginPreviousIndex, event.currentIndex)) {
            // movingPlugin.notValidPosition = true;
            console.log('cannot move here');
        } else {
            movingPlugin.notValidPosition = false;
        }

    }

    // delete  plugin from pipeline
    deletePlugin(plugin) {
        const indexOfPlugin = this.plugins.indexOf(plugin);
        this.plugins.splice(indexOfPlugin, 1);
    }
}
