/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ComponentFactoryResolver } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';
import { AoPipelineViewComponent } from '../ao-pipeline-view/ao-pipeline-view.component';

@Component({
    templateUrl: './ao-endpoint-view.component.html',
    styleUrls: ['./ao-endpoint-view.component.css']
})
export class AoEndpointViewComponent extends AoPipelineViewComponent implements OnInit, OnDestroy {

    isProcessing = false;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected pluginsService: AoPluginsService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService) {
        super(route, apiClient, componentFactoryResolver, pluginsService, snackBar);
    }

    ngOnInit() {
        super.ngOnInit();

    }

    onLoad() {
        super.onLoad();
    }


    process() {

    }

    // fake plugin list (should be retrieved using api)
    _getPlugins(): any {
        return new Promise(function (resolve, reject) {
            const plugins = [

            ];
            resolve({
                data: plugins
            });
        });
    }

}
