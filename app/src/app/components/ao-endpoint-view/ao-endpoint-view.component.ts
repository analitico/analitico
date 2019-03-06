/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ComponentFactoryResolver, ViewChild, AfterViewInit, ViewContainerRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';

import { AoViewComponent } from '../ao-view/ao-view.component';
import { JsonEditorOptions, JsonEditorComponent } from 'ang-jsoneditor';
import { AoMessageBoxService } from 'src/app/services/ao-message-box/ao-message-box';
import { AoRefreshable } from 'src/app/ao-refreshable';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { AoS24OrderSortingPredictionViewComponent } from 'src/app/plugins/ao-s24-order-sorting-prediction-view/ao-s24-order-sorting-prediction-view.component';
import { MatSort, MatTableDataSource } from '@angular/material';
import * as _ from 'lodash';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    templateUrl: './ao-endpoint-view.component.html',
    styleUrls: ['./ao-endpoint-view.component.css']
})
export class AoEndpointViewComponent extends AoViewComponent implements OnInit, OnDestroy, AoRefreshable, AfterViewInit {

    @ViewChild('inputEditor') inputEditor: JsonEditorComponent;
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;

    isProcessing = false;
    prediction: any;
    model: any;
    editorOptions: JsonEditorOptions;
    predictionEditorOptions: JsonEditorOptions;
    inputData: any;
    predictionData: any;
    predictionSamples: any;
    predictionCustomViewComponent: any;
    predictionCustomViewContainerRef: ViewContainerRef;
    predictionCustomViewInstance: IAoPluginInstance;
    alternativeModels: any;
    tableModels: any;
    endpointUrl: string;
    recipe: any;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected messageBox: AoMessageBoxService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected itemService: AoItemService) {
        super(route, apiClient, itemService);
        // initialize JSON editor
        this.editorOptions = new JsonEditorOptions();
        this.editorOptions.modes = ['code']; // set all allowed modes
        this.editorOptions.mode = 'code';

        this.predictionEditorOptions = new JsonEditorOptions();
        this.predictionEditorOptions.modes = ['view']; // set all allowed modes
        this.predictionEditorOptions.mode = 'view';
    }

    ngOnInit() {
        super.ngOnInit();

    }

    ngAfterViewInit() {
        // get the view of the anchor component
        this.predictionCustomViewContainerRef = this.aoAnchor.viewContainerRef;
        this.checkIfCustomViewCanBeLoaded();
    }


    onLoad() {
        super.onLoad();
        this.endpointUrl = 'https://' + location.hostname + '/api/endpoints/' + this.item.id + '/predict';
        this.predictionSamples = null;
        this.inputData = null;
        this.predictionData = null;
        this.predictionCustomViewComponent = null;
        this.model = null;
        this.tableModels = null;
        this.alternativeModels = null;
        this.recipe = null;
        // load model
        this.loadModel();
    }

    checkIfCustomViewCanBeLoaded() {
        if (this.predictionCustomViewContainerRef && this.predictionCustomViewComponent) {
            this.predictionCustomViewContainerRef.clear();
            const componentFactory = this.componentFactoryResolver.resolveComponentFactory(this.predictionCustomViewComponent);
            // add the component to the anchor view
            const componentRef = this.predictionCustomViewContainerRef.createComponent(componentFactory);
            this.predictionCustomViewInstance = (<IAoPluginInstance>componentRef.instance);
        }

    }


    // loads the model associated with the endpoint
    loadModel() {
        if (this.item.attributes.model_id) {
            this.itemService.loadItem(null, '/models/' + this.item.attributes.model_id)
                .then((model) => {
                    this.model = model;
                    this.loadRecipe();
                    // load other models of same recipe
                    this.loadAlternativeModels();
                    this.loadSamples();
                    // check type of alghoritm and load component to view it
                    switch (this.model.attributes.training.algorithm) {
                        case 'ml/regression':
                        case 's24/ordersorting':
                            this.predictionCustomViewComponent = AoS24OrderSortingPredictionViewComponent;
                            break;
                    }
                    this.checkIfCustomViewCanBeLoaded();
                });
        }
    }

    loadRecipe() {
        this.recipe = null;
        if (this.model.attributes && this.model.attributes.recipe_id) {
            this.itemService.loadItem(null, '/recipes/' + this.model.attributes.recipe_id)
                .then((recipe) => {
                    this.recipe = recipe;
                });
        }
    }

    // find models with the same recipe_id for switching
    loadAlternativeModels() {
        this.itemService.getModels()
            .then((models) => {
                this.alternativeModels = [];
                models.forEach(model => {
                    if (model.attributes.recipe_id === this.model.attributes.recipe_id) {
                        if (model.id === this.model.id) {
                            // push current deployed model to the top of the list
                            this.alternativeModels.unshift(model);
                        } else {
                            this.alternativeModels.push(model);
                        }
                    }
                });

                // assign data source for the table
                this.tableModels = new MatTableDataSource(this.alternativeModels);

            });
    }

    // load sample data from trained model associated with this endpoint
    loadSamples() {
        if (this.model && this.model.attributes.data) {
            let predictionSamples, trainingSamples;
            // look for training samples
            for (let i = 0, l = this.model.attributes.data.length; i < l; i++) {
                const data = this.model.attributes.data[i];
                if (data.id === 'prediction-samples.json') {
                    predictionSamples = data;
                }
                if (data.id === 'training-samples.json') {
                    trainingSamples = data;
                }
            }
            if (!predictionSamples && trainingSamples) {
                // if prediction samples not found we can use the training samples
                // because the pipeline accept the same type of data
                predictionSamples = trainingSamples;
            }
            if (predictionSamples) {
                this.apiClient.get(predictionSamples.url)
                    .then((response) => {
                        this.predictionSamples = response;
                    });
            }

        }
    }
    // execute the predict command on the endpoint
    predict() {
        if (this.isProcessing) {
            return;
        }

        let inputData;
        try {
            inputData = this.inputEditor.get();
        } catch (e) {
            return this.messageBox.show('Please enter valid json', 'Invalid input data');
        }

        this.isProcessing = true;
        this.apiClient.post('/endpoints/' + this.item.id + '/predict', inputData)
            .then((response: any) => {
                this.isProcessing = false;
                this.gotPrediction(response.data);
            })
            .catch(() => {
                this.isProcessing = false;
            });

    }
    // set the prediction response and pass to the custom view component
    gotPrediction(data) {
        this.predictionData = data;
        // set data to custom view
        this.predictionCustomViewInstance.setData(data);
    }

    // pick a random record among the predictionSamples to be used for prediction
    selectRandomSample() {
        if (this.predictionSamples && this.predictionSamples.length > 0) {
            const random = Math.floor(Math.random() * this.predictionSamples.length);
            this.inputData = { data: [this.predictionSamples[random]] };
        }
    }

    // ask to change the model associated with this endpoint
    requestToSetNewModel(model, $event) {
        $event.stopPropagation();
        $event.preventDefault();
        const subscription =
            this.messageBox.show('Do you want to change the model associated with this endpoint?',
                'Changing endpoint model', 'WARNING: this could affect your production data', 2)
                .subscribe((response) => {
                    subscription.unsubscribe();
                    if (response.result === 'yes') {
                        this.setModel(model);
                    }
                });
    }

    // sets the model_id of the endpoint and reloads item
    setModel(model) {
        this.item.attributes.model_id = model.id;
        this.saveItem()
            .then(() => {
                this.loadItem();
            });
    }
}
