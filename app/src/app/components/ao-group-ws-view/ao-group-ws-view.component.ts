/**
 * View for group of object that must be updated or filtered according to current workspace
 */
import { Component, OnInit, OnDestroy, Input, ViewChild } from '@angular/core';
import { AoGroupViewComponent } from 'src/app/components/ao-group-view/ao-group-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { MatSort, MatTableDataSource } from '@angular/material';
import * as _ from 'lodash';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-group-ws-view',
    templateUrl: './ao-group-ws-view.component.html',
    styleUrls: ['./ao-group-ws-view.component.css']
})
export class AoGroupWsViewComponent extends AoGroupViewComponent implements OnInit, OnDestroy {
    protected globalStateObserverSubscription: any; // keeps reference of observer subscription for cleanup
    private workspace: any;
    private originalItems: any;
    // bar with top items
    topItems = [];
    displayedColumns: string[] = ['attributes.title', 'attributes.created_at'];
    tableDS;

    @ViewChild(MatSort) sort: MatSort;
    @Input() newItemTitle: string;

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore, protected router: Router,
        protected itemService: AoItemService) {
        super(route, apiClient);
    }

    ngOnInit() {
        super.ngOnInit();
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
    }


    ngOnDestroy() {
        // unsubscribe to avoid memory leaks
        if (this.globalStateObserverSubscription) {
            this.globalStateObserverSubscription.unsubscribe();
        }
    }

    onGlobalStateUpdate() {
        const workspace = this.globalState.getProperty('workspace');
        if (workspace) {
            this.workspace = workspace;
            // reload items
            this.loadItems();
        }
    }

    onLoad() {
        // look at workspace and filter
        super.onLoad();
        // save original
        this.originalItems = this.items;
        // after load we want to filter
        this.filterItems();

        // take top 4 items for the top bar
        this.topItems = this.items.slice(0, 4);
        // assign data source for the table
        this.tableDS = new MatTableDataSource(this.items);
        // table fields are nested in the dictionary, hence we need an accessor to the value from the column name for sorting purpose
        this.tableDS.sortingDataAccessor = (item, property) => {
            return _.get(item, property);
        };
        this.tableDS.sort = this.sort;
    }

    filterItems() {
        if (this.originalItems && this.originalItems.length > 0) {
            this.items = this.itemService.filterItemsByDictionary(this.originalItems, { 'attributes.workspace_id': this.workspace.id });
        }
    }

    // create a new item
    addItem() {
        const workspace = this.globalState.getProperty('workspace');
        const params = { attributes: { 'workspace_id': workspace.id } };
        if (this.newItemTitle) {
            params.attributes['title'] = this.newItemTitle;
        }
        this.apiClient.post(this.baseUrl, params)
            .then((response: any) => {
                // go to new item page
                this.router.navigate([this.baseUrl + '/' + response.data.id]);
                // super.loadItems();
            });
    }

    deleteItem(item, $event) {
        $event.preventDefault();
        $event.stopPropagation();

        if (confirm('Delete?')) {
            this.apiClient.delete(this.baseUrl + '/' + item.id)
                .then((response: any) => {
                    // reload
                    super.loadItems();
                });
        }

    }

    saveItem(item) {
        return this.apiClient.patch(this.baseUrl + '/' + item.id, item)
            .then((response: any) => {

            });
    }

    changeItemTitle(item, $event) {
        $event.stopPropagation();
        $event.preventDefault();
        $event.target.blur();
        return this.saveItem(item);
    }
}
