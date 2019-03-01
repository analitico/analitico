/**
 * Home view shows a summary of all the items contained in the workspace
 */
import { Component, OnInit, OnDestroy } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoRefreshable } from 'src/app/ao-refreshable';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';

import { ActivatedRoute } from '@angular/router';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-home-view',
    templateUrl: './ao-home-view.component.html',
    styleUrls: ['./ao-home-view.component.css']
})
export class AoHomeViewComponent implements OnInit, OnDestroy, AoRefreshable {



    constructor(protected apiClient: AoApiClientService, private globalState: AoGlobalStateStore, protected route: ActivatedRoute,
        protected itemService: AoItemService) {
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
    }
    globalStateObserverSubscription: any;
    items: any;
    workspace: any;
    queryParamsSubscription: any;
    query: string;

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
        this.apiClient.get('/models')
            .then(this.addItems.bind(this));

    }

    addItems(response) {
        this.items = [];
        let items = this.itemService.filterItemsByDictionary(response.data, this.getWorkspacefilter());
        if (this.query) {
            items = this.itemService.filterItemsByString(items, this.query);
        }
        this.items = this.items.concat(items);
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
        console.log('refresh');
        this.init();
    }

}
