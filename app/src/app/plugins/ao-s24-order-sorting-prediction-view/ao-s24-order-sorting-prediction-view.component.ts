/**
 * Used to compare original record and predictions in S24 Order Sorting models
 */
import { Component, OnInit } from '@angular/core';
import { AoPluginComponent } from '../ao-plugin-component';


@Component({
    selector: 'app-ao-s24-order-sorting-prediction-view',
    templateUrl: './ao-s24-order-sorting-prediction-view.component.html',
    styles: ['.mat-list-item-content{ padding: 0 !important;}']

})
export class AoS24OrderSortingPredictionViewComponent extends AoPluginComponent implements OnInit {

    selectedRecord: any;
    selectedRecordIndex: any;

    constructor() {
        super();
    }

    ngOnInit() {
    }

    // used to set the plugin data
    setData(data: any) {
        super.setData(data);
        // auto select first record
        this.selectedRecord = data.records[0];
        this.selectedRecordIndex = 0;
    }

    changeRecord(index) {
        this.selectedRecordIndex = index;
    }
}
