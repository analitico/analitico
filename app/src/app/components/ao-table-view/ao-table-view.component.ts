import { Component, OnInit, Input } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

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
    private cacheBlockSize;

    constructor(protected  apiClient: AoApiClientService) {
        this.rowBuffer = 0;
        this.rowSelection = 'multiple';
        this.rowModelType = 'infinite';
        this.paginationPageSize = 5;
        this.cacheOverflowSize = 2;
        this.maxConcurrentDatasourceRequests = 1;
        this.infiniteInitialRowCount = 1;
        this.maxBlocksInCache = 2;
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
        const dataSource = {
            rowCount: null,
            // tslint:disable-next-line:no-shadowed-variable
            getRows: function (params) {
                console.log('asking for ' + params.startRow + ' to ' + params.endRow);
                let query = that.data + '?page={page}&pageSize={pageSize}';
                const page = (params.endRow / that.paginationPageSize) - 1;
                query = query.replace('{page}', '' + page).replace('{pageSize}', that.paginationPageSize);
                console.log('asking for ' + params.startRow + ' to ' + params.endRow + ' page ' + page + ' ' + query);
                that.apiClient.get(query)
                    .then((response) => {
                        params.successCallback(response.data, -1);
                    });
                /*setTimeout(function () {
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
                }, 500); */
            }
        };
        params.api.setDatasource(dataSource);

    }

}
