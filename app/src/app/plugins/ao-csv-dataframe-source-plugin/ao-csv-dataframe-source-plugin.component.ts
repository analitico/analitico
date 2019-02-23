/**
 * CsvDataframeSourcePlugin is used to upload a csv file that will be available
 * as a data source for further processing in the platform
 */
import { Component, OnInit, OnDestroy } from '@angular/core';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { query } from '@angular/core/src/render3';
import { MatTableDataSource } from '@angular/material';

@Component({
    selector: 'app-ao-csv-dataframe-source-plugin',
    templateUrl: './ao-csv-dataframe-source-plugin.component.html',
    styleUrls: ['./ao-csv-dataframe-source-plugin.component.css']
})
export class AoCsvDataframeSourcePluginComponent extends AoPluginComponent {
    rows: any;
    displayedColumns: any;
    tableDS: any;

    constructor(protected apiClient: AoApiClientService) {
        super();
    }
    setData(data: any) {
        super.setData(data);
        this.loadSource();
    }

    loadSource() {
        // load first 100 rows
        const url = this.data.source.url.substring(this.data.source.url.indexOf('/datasets')) + '?format=json&page=0&page_size=100';
        this.apiClient.get(url)
            .then((response: any) => {
                this.rows = response.data;
                this.buildTable();
            });
    }

    buildTable() {
        // add first column for column names
        this.displayedColumns = ['Column'];
        const tableRows = [];
        // to keep reference of the table rows during loop
        const tableRowsDic = {};
        // for each column in the schema -> add rows
        this.data.source.schema.columns.forEach(col => {
            const dic = { Column: col.name };
            tableRows.push(dic);
            // keep reference
            tableRowsDic[col.name] = dic;
        });

        this.rows.forEach((row, index) => {
            // for each row add a column with the index as the header
            this.displayedColumns.push('' + index);
            // for each column of the schema
            this.data.source.schema.columns.forEach(col => {
                // get row for this column in the transposed table
                const rowForColumn = tableRowsDic[col.name];
                // copy value in row index position
                rowForColumn[index] = row[col.name];
            });
        });
        // assign data source to table
        this.tableDS = new MatTableDataSource(tableRows);
        console.log(this.data.source.schema.columns);
    }

    columnTypeChanged() {
        // notify change
        this.notifyChange();
    }
}
