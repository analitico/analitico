import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

import * as _ from 'lodash';


@Component({
    selector: 'app-ao-nav-list',
    templateUrl: './ao-nav-list.component.html',
    styleUrls: ['./ao-nav-list.component.css']
})
export class AoNavListComponent implements OnInit {

    // it will emit the selected id
    @Output() selectedId = new EventEmitter();
    protected _filter: any;
    protected _sortFunction: any;
    protected _items: any;

    @Input() set filter(val: any) {
        if (val) {
            this._filter = val;
            this.processItems();
        }
    }
    @Input() set sort(val: any) {
        if (val) {
            this._sortFunction = val;
            this.processItems();
        }
    }
    @Input() set items(items: any) {
        this._items = items;
        this.processItems();
    }

    constructor() {}


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

    processItems() {
        if (this._items && this._items.length > 0) {
            this._items.sort(this._sortFunction);
            if (this._filter) {
                // apply filter
                this._items = AoNavListComponent.filterItems(this._items, this._filter);
            }
        }
    }

    // output the id of the selected item
    selectItem(item: any) {
        this.selectedId.emit(item.id);
    }

}
