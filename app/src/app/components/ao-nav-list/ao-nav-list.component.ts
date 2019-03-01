/**
 * Displays a list of object.
 * Can filter and sort object according to parameters.
 */
import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

import * as _ from 'lodash';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';


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
    @Input() title: string;

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
    get items(): Array<any> {
        return this._items;
    }
    @Input() set items(items: Array<any>) {
        this._items = items;
        this.processItems();
    }

    constructor(protected itemService: AoItemService) { }


    ngOnInit() {
        // this.loadListFromUrl();
    }

    processItems() {
        if (this._items && this._items.length > 0) {

            if (this._filter) {
                // apply filter
                this._items = this.itemService.filterItemsByDictionary(this._items, this._filter);
            }
            // sort items
            if (this._sortFunction) {
                this._items.sort(this._sortFunction);
            }
        }
    }

    // output the id of the selected item
    selectItem(item: any) {
        this.selectedId.emit(item.id);
    }

}
