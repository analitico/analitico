import { Component, ComponentFactoryResolver } from '@angular/core';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';

@Component({
    selector: 'app-ao-dataframe-pipeline-plugin',
    templateUrl: './ao-dataframe-pipeline-plugin.component.html',
    styleUrls: ['./ao-dataframe-pipeline-plugin.component.css']
})
export class AoDataframePipelinePluginComponent extends AoPipelinePluginComponent {

    constructor(componentFactoryResolver: ComponentFactoryResolver) {
        super(componentFactoryResolver);
    }

    isSourcePlugin(plugin): boolean {
        return plugin.name.indexOf('SourcePlugin') > 0;
    }

    // verify if the plugin can be moved in this position
    canPluginBeMoved(pluginPreviousIndex, pluginCurrentIndex) {
        const movingPlugin = this.plugins[pluginPreviousIndex];
        if (pluginCurrentIndex === 0) {
            // we are placing to the top, it should be a SOURCE plugin
            if (!this.isSourcePlugin(movingPlugin)) {
                return false;
            }
        } else if (pluginPreviousIndex === 0) {
            // we are moving the top, check that the next one is ok to be the source
            if (this.plugins.length > 1) {
                if (!this.isSourcePlugin(this.plugins[1])) {
                    return false;
                }
            }
        }
        return true;
    }

    // verifies if the plugin can be added in the current position
    canPluginBeAdded(plugin, pluginCurrentIndex) {
        const isItASourcePlugin = this.isSourcePlugin(plugin);
        if ((pluginCurrentIndex === 0 && !isItASourcePlugin) || (pluginCurrentIndex > 0 && isItASourcePlugin)) {
            // data source plugin can be placed only on top
            return false;
        }
        return true;
    }
}
