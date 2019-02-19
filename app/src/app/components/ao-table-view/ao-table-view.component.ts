import { Component, OnInit, Input } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    selector: 'app-ao-table-view',
    templateUrl: './ao-table-view.component.html',
    styleUrls: ['./ao-table-view.component.css']
})
export class AoTableViewComponent implements OnInit {

    columns: any;
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


    rowModelType: string;
    maxBlocksInCache: number;
    cacheBlockSize: number;
    cacheOverflowSize: number;
    gridParams: any;

    constructor(protected apiClient: AoApiClientService) {
        this.rowModelType = 'infinite';
        this.maxBlocksInCache = 2;
        this.cacheBlockSize = 25;
        this.cacheOverflowSize = 100;
    }

    ngOnInit() {
    }

    initTable() {
        if (this._data && this._data.schema) {
            this.columns = [];
            if (!this._isTransposed) {
                // build array of columns using schema.columns
                const that = this;
                this._data.schema.columns.forEach(element => {
                    const col = {
                        headerName: element.name,
                        field: element.name
                    };
                    that.columns.push(col);
                });
            }
            this.initData();
        }
    }

    onGridReady(params) {
        this.gridParams = params;
        this.initData();
    }

    initData() {
        const that = this;
        if (this.gridParams && this._data) {
            const dataSource = {
                rowCount: null,
                // tslint:disable-next-line:no-shadowed-variable
                getRows: function (params) {
                    let query = that._data.jsonUrl + '?page={page}&page_size={pageSize}&meta=True';
                    const itemsRequired = params.endRow - params.startRow;
                    const page = (params.endRow / itemsRequired) - 1;
                    query = query.replace('{page}', '' + page).replace('{pageSize}', '' + itemsRequired);
                    // console.log('asking for ' + params.startRow + ' to ' + params.endRow + ' page ' + page + ' ' + query);
                    that.apiClient.get(query)
                        .then((response: any) => {
                            // https://www.ag-grid.com/javascript-grid-infinite-scrolling/
                            // lastRow should be the index of the last row if known, otherwise -1
                            params.successCallback(response.data, -1);
                        });
                }
            };
            this.gridParams.api.setDatasource(dataSource);
        }
    }
}
