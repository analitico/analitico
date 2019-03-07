/**
 * Home view shows a summary of all the items contained in the workspace
 */
import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoRefreshable } from 'src/app/ao-refreshable';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';

import { ActivatedRoute } from '@angular/router';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { MatTableDataSource, MatSort } from '@angular/material';
import * as _ from 'lodash';

@Component({
    selector: 'app-ao-home-view',
    templateUrl: './ao-home-view.component.html',
    styleUrls: ['./ao-home-view.component.css']
})
export class AoHomeViewComponent implements OnInit, OnDestroy, AoRefreshable {

    @ViewChild(MatSort) sort: MatSort;

    constructor(protected apiClient: AoApiClientService, private globalState: AoGlobalStateStore, protected route: ActivatedRoute,
        protected itemService: AoItemService) {
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
    }
    globalStateObserverSubscription: any;
    items: any;
    workspace: any;
    queryParamsSubscription: any;
    query: string;
    displayedColumns: string[] = ['type', 'attributes.title', 'attributes.updated_at'];
    tableDS;

    ngOnInit() {
        // subscribe to query parameters changes to get search query
        this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
            if (this.query !== params.q) {
                this.query = params.q;
                this.refresh();
            }
        });
    }

    ngOnDestroy() {
        // clean up
        if (this.queryParamsSubscription) {
            this.queryParamsSubscription.unsubscribe();
        }
    }

    init() {
        console.log('init');
        this._getObjects();
    }

    // fake method to return objects
    _getObjects() {
        this.items = [];
        // only load on search
        if (this.query) {
            this.itemService.getItems()
                .then((items) => {
                    this.items = [];
                    this.addItems(items.datasets);
                    this.addItems(items.recipes);
                    this.addItems(items.models);
                    this.addItems(items.endpoints);
                });
        }

    }

    addItems(items) {
        // filter by workspace
        items = this.itemService.filterItemsByDictionary(items, this.getWorkspacefilter());
        if (this.query) {
            // filter by query
            items = this.itemService.filterItemsByString(items, this.query);
        }
        this.items = this.items.concat(items);
        this.tableDS = new MatTableDataSource(this.items);
        // table fields are nested in the dictionary, hence we need an accessor to the value from the column name for sorting purpose
        this.tableDS.sortingDataAccessor = (item, property) => {
            return _.get(item, property);
        };
        this.tableDS.sort = this.sort;
    }

    getWorkspacefilter() {
        return this.workspace ? { 'attributes.workspace_id': this.workspace.id } : null;
    }


    onGlobalStateUpdate() {
        this.workspace = this.globalState.getProperty('workspace');
        if (this.workspace) {
            this.init();
        }
    }

    // receive refresh updates
    refresh() {
        this.init();
    }

}
