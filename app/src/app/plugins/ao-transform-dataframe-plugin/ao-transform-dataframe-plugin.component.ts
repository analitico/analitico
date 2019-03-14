/**
 * TransformDataframePlugin can apply a schema to a dataframe and can be used to:
 * - drop columns you don't need
 * - apply a type to a column (eg. change a string to a date)
 * - reorder columns in a dataframe (eg. put the label last)
 * - rename columns
 * - make a column the index of the dataframe
 */



import { Component, OnInit } from '@angular/core';
import { AoPluginComponent } from '../ao-plugin-component';
import { MatTableDataSource } from '@angular/material';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    selector: 'app-ao-transform-dataframe-plugin',
    templateUrl: './ao-transform-dataframe-plugin.component.html',
    styleUrls: ['./ao-transform-dataframe-plugin.component.css']
})
export class AoTransformDataframePluginComponent extends AoPluginComponent implements OnInit {
    rows: any;
    displayedColumns: any;
    tableDS: any;
    constructor(protected apiClient: AoApiClientService) {
        super();
    }

    ngOnInit() {
    }

    setData(data: any) {
        super.setData(data);
        this.loadSource();
    }

    loadSource() {
        // load first 100 rows
        // TODO find a better way to get the URL
        return;
        const url = this.data.source.url.substring(this.data.source.url.indexOf('/datasets')) + '?format=json&page=0&page_size=100';
        this.apiClient.get(url)
            .then((response: any) => {
                this.rows = response.data;
                this.buildTable();
            })
            .catch((e) => { });
    }

    buildTable() {
        // add first column for column names
        this.displayedColumns = ['Column'];
        const tableRows = [];
        // to keep reference of the table rows during loop
        const tableRowsDic = {};

        if (!this.data.source.schema) {
            this.data.source.schema = { columns: [] };
            // build from data
            const firstDataRow = this.rows[0];
            for (const key in firstDataRow) {
                if (firstDataRow.hasOwnProperty(key)) {
                    this.data.source.schema.columns.push({
                        name: key
                    });
                }
            }
        }
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
    }

    columnTypeChanged() {
        // notify change
        this.notifyChange();
    }

}
