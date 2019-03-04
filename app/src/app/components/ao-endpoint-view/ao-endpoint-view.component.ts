/**
 * Dataset is used to process data through plugins.
 */
import { Component, OnInit, OnDestroy, ComponentFactoryResolver, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoPluginsService } from 'src/app/services/ao-plugins/ao-plugins.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';

import { AoViewComponent } from '../ao-view/ao-view.component';
import { JsonEditorOptions, JsonEditorComponent } from 'ang-jsoneditor';
import { AoMessageBoxService } from 'src/app/services/ao-message-box/ao-message-box';
import { AoRefreshable } from 'src/app/ao-refreshable';

@Component({
    templateUrl: './ao-endpoint-view.component.html',
    styleUrls: ['./ao-endpoint-view.component.css']
})
export class AoEndpointViewComponent extends AoViewComponent implements OnInit, OnDestroy, AoRefreshable {

    @ViewChild('inputEditor') inputEditor: JsonEditorComponent;

    isProcessing = false;
    prediction: any;
    model: any;
    editorOptions: JsonEditorOptions;
    predictionEditorOptions: JsonEditorOptions;
    inputData: any;
    predictionData: any;
    predictionSamples: any;

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected jobService: AoJobService,
        protected messageBox: AoMessageBoxService) {
        super(route, apiClient);
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

    onLoad() {
        super.onLoad();
        this.predictionSamples = null;
        this.inputData = null;
        this.predictionData = null;
        // load model
        this.loadModel();
    }


    // loads the model associated with the endpoint
    loadModel() {
        if (this.item.attributes.model_id) {
            this.apiClient.get('/models/' + this.item.attributes.model_id)
                .then((response) => {
                    this.model = response.data;
                    this.loadSamples();
                });
        }
    }

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
    // execute the process command on the dataset and refresh status when finished
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
                this.gotPrediction(response);
            })
            .catch(() => {
                this.isProcessing = false;
            });

    }

    gotPrediction(data) {
        this.predictionData = data;
    }

    selectRandomSample() {
        if (this.predictionSamples && this.predictionSamples.length > 0) {
            const random = Math.floor(Math.random() * this.predictionSamples.length);
            this.inputData = { data: [this.predictionSamples[random]] };
        }

    }
}
