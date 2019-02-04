/**
    A plugin that creates a linear workflow by chaining together other plugins.
    Plugins that are chained in a pipeline need to take a single input and have
    a single output of the same kind so they same object can be processed from
    the first, to the next and down to the last, then returned to caller as if
    the process was just one logical operation. PipelinePlugin can be used to
    for example to construct ETL (extract, transform, load) workflows.
 */

import { Component, OnInit, OnDestroy, ViewChild, ComponentFactoryResolver } from '@angular/core';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';

@Component({
    selector: 'app-ao-pipeline-plugin',
    templateUrl: './ao-pipeline-plugin.component.html',
    styleUrls: ['./ao-pipeline-plugin.component.css']
})
export class AoPipelinePluginComponent extends AoPluginComponent {
    // list of plugins of the pipeline
    plugins: any;
    pluginsService: any;
    // this is the object where we will insert the child components
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;
    constructor(private componentFactoryResolver: ComponentFactoryResolver) {
        super();
    }

    setData(data: any) {
        super.setData(data);
        if (data && data.plugins) {
            this.plugins = data.plugins;
            this.loadPlugins();
        }
    }

    // loads all the plugins
    loadPlugins(): void {
        this.plugins.forEach((pluginData, index) => {
            this.loadPlugin(pluginData, index);
        });
    }

    // load the plugin
    loadPlugin(pluginData: any, index: number): void {
        // find the class name of the plugin
        const pluginName = pluginData.name.split('.')[2];
        // get the plugin component
        const plugin = this.pluginsService.getPlugin(pluginName);
        // if we have found the plugin...
        if (plugin) {
            // get the plugin component factory
            const componentFactory = this.componentFactoryResolver.resolveComponentFactory(plugin);
            // get the view of the anchor component
            const viewContainerRef = this.aoAnchor.viewContainerRef;
            // clear the view
            viewContainerRef.clear();
            // add the component to the anchor view
            const componentRef = viewContainerRef.createComponent(componentFactory);
            const instance = (<IAoPluginInstance>componentRef.instance);
            // send data
            instance.setData(pluginData);
            // subscribe to update
            instance.onNewDataSubject.subscribe(this.onNewData.bind(this, index));
        } else {
            throw new Error('Missing plugin, cannot build pipeline');
        }
    }

    onNewData(index: number, pluginData: any): void {
        // changed data in a specific plugin
        this.plugins[index] = pluginData;
        // notify upper levels
        this.onNewDataSubject.next();
    }
}
