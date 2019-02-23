import { Component, ComponentFactoryResolver } from '@angular/core';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';

@Component({
    selector: 'app-ao-endpoint-pipeline-plugin',
    templateUrl: './ao-endpoint-pipeline-plugin.component.html',
    styleUrls: ['./ao-endpoint-pipeline-plugin.component.css']
})
export class AoEndpointPipelinePluginComponent extends AoPipelinePluginComponent {

    constructor(componentFactoryResolver: ComponentFactoryResolver) {
        super(componentFactoryResolver);
    }


}
