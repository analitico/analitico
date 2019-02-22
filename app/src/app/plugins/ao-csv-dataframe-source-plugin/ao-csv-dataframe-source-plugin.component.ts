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
        this.displayedColumns = ['columnName'];
        const tableRows = [];
        const tableRowsDic = {};
        this.data.source.schema.columns.forEach(col => {
            const dic = {columnName: col.name};
            tableRows.push(dic);
            // keeps reference
            tableRowsDic[col.name] = dic;
        });
        this.rows.forEach((row, index) => {
            // add column
            this.displayedColumns.push('' + index);
            this.data.source.schema.columns.forEach(col => {
                // get row for this column
                const rowForColumn = tableRowsDic[col.name];
                // copy column value in row index position
                rowForColumn[index] = row[col.name];
            });
        });
        this.tableDS = new MatTableDataSource(tableRows);
    }
}
