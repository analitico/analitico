import { Component, OnInit, Input } from '@angular/core';
import { HttpClient } from "@angular/common/http";

@Component({
    selector: 'app-ao-table-view',
    templateUrl: './ao-table-view.component.html',
    styleUrls: ['./ao-table-view.component.css']
})
export class AoTableViewComponent implements OnInit {

    columns: any;

    private _schema: any;
    get schema() {
        return this._schema;
    }
    @Input() set schema(val: string) {
        if (val) {
            this._schema = val;
            this.initTable();
        }
    }

    private _data: any;
    get data() {
        return this._data;
    }
    @Input() set data(val: string) {
        if (val) {
            this._data = val;
            this.initTable();
        }
    }

    private _isTransposed: any;
    get isTransposed() {
        return this._isTransposed;
    }
    @Input() set isTransposed(val: string) {
        this._isTransposed = val;
        this.initTable();
    }

    private rowBuffer;
    private rowSelection;
    private rowModelType;
    private paginationPageSize;
    private cacheOverflowSize;
    private maxConcurrentDatasourceRequests;
    private infiniteInitialRowCount;
    private maxBlocksInCache;

    constructor(private http: HttpClient) {
        this.rowBuffer = 0;
        this.rowSelection = 'multiple';
        this.rowModelType = 'infinite';
        this.paginationPageSize = 50;
        this.cacheOverflowSize = 2;
        this.maxConcurrentDatasourceRequests = 1;
        this.infiniteInitialRowCount = 100;
        this.maxBlocksInCache = 10;
    }

    ngOnInit() {

        this.initTable();
    }

    initTable() {
        if (this._schema) {
            this.columns = [];
            if (!this._isTransposed) {
                // build array of columns using schema.columns
                const that = this;
                this._schema.columns.forEach(element => {
                    const col = {
                        headerName: element.name,
                        field: element.name
                    };
                    that.columns.push(col);
                });
            }
        }
    }

    onGridReady(params) {
        const that = this;
        this.http
            .get("/data.json")
            .subscribe((data: Array<{}>) => {
                const dataSource = {
                    rowCount: null,
                    // tslint:disable-next-line:no-shadowed-variable
                    getRows: function (params) {
                        console.log('asking for ' + params.startRow + ' to ' + params.endRow);
                        setTimeout(function () {
                            const rowsThisPage = data.slice(params.startRow, params.endRow);
                            let lastRow = -1;
                            if (data.length <= params.endRow) {
                                lastRow = data.length;
                            }
                            if (!this._isTransposed) {
                                params.successCallback(rowsThisPage, lastRow);
                            } else {
                                // we need to build the table

                            }
                        }, 500);
                    }
                };
                params.api.setDatasource(dataSource);
            });
    }

}
