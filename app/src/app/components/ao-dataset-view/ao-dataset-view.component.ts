import { Component, OnInit, OnDestroy, ViewChild, ComponentFactoryResolver } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';
@Component({
    templateUrl: './ao-dataset-view.component.html',
    styleUrls: ['./ao-dataset-view.component.css']
})
export class AoDatasetViewComponent extends AoViewComponent implements OnInit {
    // this is the object where we will insert the child components
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;

    title: string;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        private componentFactoryResolver: ComponentFactoryResolver,
        private pluginsService: AoPluginsService) {
        super(route, apiClient);
    }
    static hasPlugin(item): boolean {
        return typeof item.attributes.plugin !== 'undefined' && item.attributes.plugin;
    }
    ngOnInit() {
        super.ngOnInit();
    }


    onLoad() {
        if (this.item.attributes.title) {
            this.title = this.item.attributes.title;
        }
        // check if we have at least one plugin
        if (!AoDatasetViewComponent.hasPlugin(this.item)) {
            // add Pipeline plugin
            this.item.attributes.plugin = {
                'type': 'analitico/plugin',
                'name': 'analitico.plugin.PipelinePlugin',
                'plugins': []
            };
            // save
            return this.saveItem();
        }
        this.loadPlugin();

    }
    // load the plugin
    loadPlugin() {
        const pluginData = this.item.attributes.plugin;
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
            (<IAoPluginInstance>componentRef.instance).pluginsService = this.pluginsService;
            // pass data to the component
            (<IAoPluginInstance>componentRef.instance).dataSubject.next(pluginData);
        }
    }
}
