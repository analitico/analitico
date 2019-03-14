/**
 * Model represents a trained model that can be associated with an endpoint to be consumed
 */
import { Component, OnInit, Input } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { MatTableDataSource } from '@angular/material';


@Component({
    selector: 'app-ao-model-view',
    templateUrl: './ao-model-view.component.html',
    styleUrls: ['./ao-model-view.component.css']
})
export class AoModelViewComponent extends AoViewComponent implements OnInit {
    recipe: any;
    tableModels: any;
    alternativeModels: any;
    featureGraph: any;
    confusionMatrixGraph: any;
    _model: any;

    get model() {
        return this._model;
    }
    @Input() set model(val: any) {
        if (val) {
            this._model = val;
            this.load();
        }
    }

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected itemService: AoItemService,
        protected router: Router) {
        super(route, apiClient, itemService, snackBar);
    }

    ngOnInit() {
        super.ngOnInit();
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
                    x:  (classes.concat([])).reverse(),
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
    }

}
