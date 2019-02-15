import { Component, ComponentFactoryResolver } from '@angular/core';
import { AoPipelinePluginComponent } from 'src/app/plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';

@Component({
    selector: 'app-ao-recipe-pipeline-plugin',
    templateUrl: './ao-recipe-pipeline-plugin.component.html',
    styleUrls: ['./ao-recipe-pipeline-plugin.component.css']
})
export class AoRecipePipelinePluginComponent extends AoPipelinePluginComponent {

    constructor(componentFactoryResolver: ComponentFactoryResolver) {
        super(componentFactoryResolver);
    }


}
