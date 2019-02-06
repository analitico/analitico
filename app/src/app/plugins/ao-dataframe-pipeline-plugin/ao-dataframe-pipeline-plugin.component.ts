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


}
