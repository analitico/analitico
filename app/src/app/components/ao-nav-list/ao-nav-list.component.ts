import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import * as _ from 'lodash';


@Component({
    selector: 'app-ao-nav-list',
    templateUrl: './ao-nav-list.component.html',
    styleUrls: ['./ao-nav-list.component.css']
})
export class AoNavListComponent implements OnInit {
    private _url: any;
    @Input() set url(val: string) {
        if (val) {
            this._url = val;
            this.loadListFromUrl();
        }
    }
    // it will emit the selected id
    @Output() selectedId = new EventEmitter();
    private _filter: any;
    @Input() set filter(val: any) {
        if (val) {
            this._filter = val;
            this.loadListFromUrl();
        }
    }
    @Input() set sort(val: any) {
        if (val) {
            this._sortFunction = val;
            this.loadListFromUrl();
        }
    }
    items: any;
    private _sortFunction: any;


    constructor(private apiClient: AoApiClientService) {
        // define default sort function on created_at attributes
        this._sortFunction = function (a, b) {
            return a.attributes.created_at > b.attributes.created_at ? -1 : 1;
        };
    }

    // filters an array of objects using a dictionary
    static filterItems(items, filter): any {
        return items.filter((item) => {
            for (const filterKey in filter) {
                if (filter.hasOwnProperty(filterKey)) {
                    // get the value specified in the filter path
                    const value = _.get(item, filterKey);
                    const filterValue = filter[filterKey];
                    // compare object value with filter value
                    if (value !== filterValue) {
                        return false;
                    }
                }
            }
            return true;
        });
    }

    ngOnInit() {
        // this.loadListFromUrl();
    }

    // loads an url  that provides a list of objects with id and title properties
    loadListFromUrl() {
        this.apiClient.get(this._url)
            .then((response: any) => {
                this.items = response.data;
                if (this.items && this.items.length > 0) {
                    this.items.sort(this._sortFunction);
                    if (this._filter) {
                        // apply filter
                        this.items = AoNavListComponent.filterItems(this.items, this._filter);
                    }
                }
            });
    }


    // output the id of the selected item
    selectItem(item: any) {
        this.selectedId.emit(item.id);
    }

    // delete an item using DELETE request
    deleteItem(item: any) {
        this.apiClient.delete(this._url + '/' + item.id)
            .then((response: any) => {
                this.loadListFromUrl();
            });
    }
}
