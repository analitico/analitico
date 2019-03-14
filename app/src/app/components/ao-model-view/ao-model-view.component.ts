/**
 * Model represents a trained model that can be associated with an endpoint to be consumed
 */
import { Component, OnInit, Input, ViewChild, ViewContainerRef, ComponentFactoryResolver, AfterViewInit } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { MatTableDataSource } from '@angular/material';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoS24OrderSortingPredictionViewComponent } from 'src/app/plugins/ao-s24-order-sorting-prediction-view/ao-s24-order-sorting-prediction-view.component';
import { IAoPluginInstance } from 'src/app/plugins/ao-plugin-instance-interface';
import { JsonEditorComponent, JsonEditorOptions } from 'ang-jsoneditor';
import { AoMessageBoxService } from 'src/app/services/ao-message-box/ao-message-box';


@Component({
    selector: 'app-ao-model-view',
    templateUrl: './ao-model-view.component.html',
    styleUrls: ['./ao-model-view.component.css']
})
export class AoModelViewComponent implements OnInit, AfterViewInit {
    recipe: any;
    tableModels: any;
    alternativeModels: any;
    featureGraph: any;
    confusionMatrixGraph: any;
    _model: any;
    predictionSamples: any;
    editorOptions: JsonEditorOptions;
    predictionCustomViewComponent: any;
    predictionCustomViewContainerRef: ViewContainerRef;
    predictionCustomViewInstance: IAoPluginInstance;
    isProcessing = false;
    predictionEditorOptions: JsonEditorOptions;
    inputData: any;
    predictionData: any;

    @ViewChild('inputEditor') inputEditor: JsonEditorComponent;
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;

    get model() {
        return this._model;
    }
    @Input() set model(val: any) {
        if (val) {
            this._model = val;
            this.load();
        }
    }

    constructor(protected apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected itemService: AoItemService,
        protected componentFactoryResolver: ComponentFactoryResolver,
        protected router: Router,
        protected messageBox: AoMessageBoxService) {

        // initialize JSON editor
        this.editorOptions = new JsonEditorOptions();
        this.editorOptions.modes = ['code']; // set all allowed modes
        this.editorOptions.mode = 'code';

        this.predictionEditorOptions = new JsonEditorOptions();
        this.predictionEditorOptions.modes = ['view']; // set all allowed modes
        this.predictionEditorOptions.mode = 'view';
    }

    ngOnInit() {

    }

    ngAfterViewInit() {
        // get the view of the anchor component
        this.predictionCustomViewContainerRef = this.aoAnchor.viewContainerRef;
        this.checkIfCustomViewCanBeLoaded();
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

    load() {
        this.featureGraph = null;
        if (this.model.attributes.training && this.model.attributes.training.scores
            && this.model.attributes.training.scores.features_importance) {
            this.featureGraph = {
                data: [{ x: [], y: [], type: 'bar', orientation: 'h' }],
                layout: {
                    yaxis: {
                        type: 'category',
                        automargin: true
                    },
                }
            };
            for (const feature in this.model.attributes.training.scores.features_importance) {
                if (this.model.attributes.training.scores.features_importance.hasOwnProperty(feature)) {
                    this.featureGraph.data[0].y.unshift(feature);
                    this.featureGraph.data[0].x.unshift(this.model.attributes.training.scores.features_importance[feature]);
                }
            }
        }

        this.confusionMatrixGraph = null;
        if (this.model.attributes.training && this.model.attributes.training.scores
            && this.model.attributes.training.scores.confusion_matrix) {
            const classes = [];
            this.model.attributes.training.data.classes.forEach(element => {
                classes.push(element);
            });
            const matrix = this.model.attributes.training.scores.confusion_matrix.concat([]);
            matrix.forEach(element => {
                element.reverse();
            });
            this.confusionMatrixGraph = {
                data: [{
                    x: (classes.concat([])).reverse(),
                    y: classes,
                    z: matrix,
                    type: 'heatmap'
                }], layout: {
                    yaxis: {
                        type: 'category',
                        automargin: true
                    },
                }
            };
        }

        this.loadSamples();

        // check type of alghoritm and load component to view it
        switch (this.model.attributes.training.algorithm) {
            case 'ml/regression':
            case 's24/ordersorting':
                this.predictionCustomViewComponent = AoS24OrderSortingPredictionViewComponent;
                break;
        }
        // show it
        this.checkIfCustomViewCanBeLoaded();
    }
    // load sample data from trained model associated with this endpoint
    loadSamples() {
        if (this.model && this.model.attributes.data) {
            let predictionSamples;
            // look for training samples
            for (let i = 0, l = this.model.attributes.data.length; i < l; i++) {
                const data = this.model.attributes.data[i];
                if (data.id === 'prediction-samples.json') {
                    predictionSamples = data;
                    break;
                }
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
       /* this.apiClient.post('/endpoints/' + this.item.id + '/predict', inputData)
            .then((response: any) => {
                this.isProcessing = false;
                this.gotPrediction(response.data);
            })
            .catch(() => {
                this.isProcessing = false;
            }); */

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
