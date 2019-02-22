import { Injectable } from '@angular/core';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';
import { AoDataframePipelinePluginComponent } from 'src/app/plugins/ao-dataframe-pipeline-plugin/ao-dataframe-pipeline-plugin.component';
// tslint:disable-next-line:max-line-length
import { AoCsvDataframeSourcePluginComponent } from 'src/app/plugins/ao-csv-dataframe-source-plugin/ao-csv-dataframe-source-plugin.component';
import { AoRawJsonPluginComponent } from 'src/app/plugins/ao-raw-json-plugin/ao-raw-json-plugin.component';
import { AoRecipePipelinePluginComponent } from 'src/app/plugins/ao-recipe-pipeline-plugin/ao-recipe-pipeline-plugin.component';
@Injectable({
    providedIn: 'root'
})
export class AoPluginsService {

    constructor() { }

    getPlugin(pluginName: string): any {
        switch (pluginName) {
            case 'PipelinePlugin':
                return AoPipelinePluginComponent;
            case 'DataframePipelinePlugin':
                return AoDataframePipelinePluginComponent;
            case 'RecipePipelinePlugin':
                return AoRecipePipelinePluginComponent;
            case 'CsvDataframeSourcePlugin':
                return AoCsvDataframeSourcePluginComponent;
            default:
                // not supported plugin are managed with a raw json editor
                return AoRawJsonPluginComponent;
        }
        return null;
    }
}
