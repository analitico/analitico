/**
 * CsvDataframeSourcePlugin is used to upload a csv file that will be available
 * as a data source for further processing in the platform
 */
import { Component, OnInit, OnDestroy } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';

@Component({
    selector: 'app-ao-csv-dataframe-source-plugin',
    templateUrl: './ao-csv-dataframe-source-plugin.component.html',
    styleUrls: ['./ao-csv-dataframe-source-plugin.component.css']
})
export class AoCsvDataframeSourcePluginComponent extends AoPluginComponent implements OnInit {
    dataSubject: BehaviorSubject<any>;
    data: any;

    constructor() {
        super();
        this.dataSubject = new BehaviorSubject({});
    }

    ngOnInit() {
        // wait to receive data from parent object
        this.dataSubject.subscribe(this.onData.bind(this));
    }

    onData(data: any) {
       this.data = data;
    }

}
