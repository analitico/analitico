/**
 * Dataset is used to process data through plugins.
 */
import { Component, ComponentFactoryResolver, ViewChild, AfterViewInit, ViewContainerRef, Input, OnDestroy } from '@angular/core';
import { formatDate } from '@angular/common';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

import { MatSnackBar } from '@angular/material/snack-bar';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';


import { JsonEditorOptions, JsonEditorComponent } from 'ang-jsoneditor';
import { AoMessageBoxService } from 'src/app/services/ao-message-box/ao-message-box';

import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { AoS24OrderSortingPredictionViewComponent } from 'src/app/plugins/ao-s24-order-sorting-prediction-view/ao-s24-order-sorting-prediction-view.component';

import * as _ from 'lodash';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-endpoint-view',
    templateUrl: './ao-endpoint-view.component.html',
    styleUrls: ['./ao-endpoint-view.component.css']
})
export class AoEndpointViewComponent implements AfterViewInit, OnDestroy {

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
    _endpoint: any;
    predictionPollingInterval: any;
    livePredictions: any;
    predictionPerformanceGraph: any;

    PREDICTION_POLL_TIME = 30000;

    get endpoint() {
        return this._endpoint;
    }
    @Input() set endpoint(val: any) {
        if (val) {
            this._endpoint = val;
            this.onLoad();
        }
    }

    constructor(protected apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected messageBox: AoMessageBoxService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected itemService: AoItemService) {

        // initialize JSON editor
        this.editorOptions = new JsonEditorOptions();
        this.editorOptions.modes = ['code']; // set all allowed modes
        this.editorOptions.mode = 'code';
        this.editorOptions.mainMenuBar = false;

        this.predictionEditorOptions = new JsonEditorOptions();
        this.predictionEditorOptions.modes = ['view']; // set all allowed modes
        this.predictionEditorOptions.mode = 'view';
        this.predictionEditorOptions.mainMenuBar = false;
    }

    ngAfterViewInit() {
        // get the view of the anchor component
        this.predictionCustomViewContainerRef = this.aoAnchor.viewContainerRef;
        this.checkIfCustomViewCanBeLoaded();
    }

    ngOnDestroy() {
        this.stopPollingLivePredictions();
    }


    onLoad() {
        this.stopPollingLivePredictions();
        this.endpointUrl = 'https://' + location.hostname + '/api/endpoints/' + this.endpoint.id + '/predict';
        this.predictionSamples = null;
        this.inputData = null;
        this.predictionData = null;
        this.predictionCustomViewComponent = null;
        this.model = null;
        this.tableModels = null;
        this.alternativeModels = null;
        this.recipe = null;
        this.livePredictions = null;
        // load model
        this.loadModel();
        this.pollLivePredictions();
    }

    // stop polling the log
    stopPollingLivePredictions() {
        if (this.predictionPollingInterval) {
            clearTimeout(this.predictionPollingInterval);
            this.predictionPollingInterval = null;
        }
    }
    // schedule a log poll
    schedulePollLivePredictions() {
        this.stopPollingLivePredictions();
        this.predictionPollingInterval = setTimeout(this.pollLivePredictions.bind(this), this.PREDICTION_POLL_TIME);
    }
    // polls the endpoint logs to find predictions.
    pollLivePredictions() {
        this.stopPollingLivePredictions();
        this.apiClient.get(this.endpoint.links.self + '/logs?sort=-created_at')
            .then((response) => {
                if (response.data && response.data.length > 0) {
                    // filter only predictions
                    let newPredictions = this.itemService.getItemsByAttribute(response.data, 'attributes.title', 'endpoint/predict');
                    if (this.livePredictions) {
                        // compare and check which is new in order to show "ticker" animation
                        /*newPredictions.unshift({
                            "type": "analitico/log",
                            "id": "lg_" + (new Date()).getTime(),
                            "attributes": {
                                "item_id": "ep_s24_outofstock",
                                "level": 20,
                                "title": "endpoint/predict",
                                "created_at": (new Date()).toISOString()
                            }
                        }); */
                    }
                    const predictionTimes = [];
                    const predictionPerformanceTime = [];
                    let i = 0;
                    newPredictions = newPredictions.sort(function (a, b) {
                        return a.attributes.created_at > b.attributes.created_at ? -1 : 1;
                    });
                    newPredictions.forEach((prediction, index) => {
                        if (this.livePredictions) {
                            if (!this.itemService.getItemById(this.livePredictions, prediction.id)) {
                                prediction.isNew = true;
                            }
                        }
                        if (prediction.attributes.prediction && prediction.attributes.prediction.performance.total_ms) {
                            predictionTimes.unshift(formatDate(prediction.attributes.created_at, 'yyyy-MM-dd HH:mm:ss', 'en'));
                            predictionPerformanceTime.unshift(prediction.attributes.prediction.performance.total_ms);
                            i++;
                        }

                    });
                    this.livePredictions = newPredictions;



                    this.predictionPerformanceGraph = {
                        data: [{
                            x: predictionTimes, y: predictionPerformanceTime, type: 'scatter', mode: 'markers',
                            marker: {
                                size: 12
                            },
                        }],
                        layout: {
                            xaxis: {
                                showgrid: false,
                                zeroline: false
                            },
                            yaxis: {
                                automargin: true
                            },
                        }
                    };
                } else {
                    this.livePredictions = null;
                }
                this.schedulePollLivePredictions();
            })
            .catch((e) => {
                this.schedulePollLivePredictions();
            });
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
        if (this.endpoint.attributes.model_id) {
            this.itemService.loadItem(null, '/models/' + this.endpoint.attributes.model_id)
                .then((model) => {
                    this.model = model;
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
        this.apiClient.post('/endpoints/' + this.endpoint.id + '/predict', inputData)
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
}
