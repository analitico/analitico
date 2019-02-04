import { Injectable } from '@angular/core';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';
// tslint:disable-next-line:max-line-length
import { AoCsvDataframeSourcePluginComponent } from 'src/app/plugins/ao-csv-dataframe-source-plugin/ao-csv-dataframe-source-plugin.component';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';

@Injectable({
    providedIn: 'root'
})
export class AoPluginsService {

    constructor() { }

    getPlugin(pluginName: string): any {
        switch (pluginName) {
            case 'PipelinePlugin':
                return AoPipelinePluginComponent;
            case 'CsvDataframeSourcePlugin':
                return AoCsvDataframeSourcePluginComponent;
        }
        return null;
    }
}
