/**
 * View for group of object that must be updated or filtered according to current workspace
 */
import { Component, OnInit, OnDestroy, Input } from '@angular/core';
import { AoGroupViewComponent } from 'src/app/components/ao-group-view/ao-group-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';

@Component({
    selector: 'app-ao-group-ws-view',
    templateUrl: './ao-group-ws-view.component.html',
    styleUrls: ['./ao-group-ws-view.component.css']
})
export class AoGroupWsViewComponent extends AoGroupViewComponent implements OnInit, OnDestroy {
    protected globalStateObserverSubscription: any; // keeps reference of observer subscription for cleanup
    private workspace: any;
    private originalItems: any;

    @Input() newItemTitle: string;

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore) {
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
            // re filter data
            this.filterItems();
        }
    }

    onLoad() {
        // look at workspace and filter
        super.onLoad();
        // save original
        this.originalItems = this.items;
        // after load we want to filter
        this.filterItems();
    }

    filterItems() {
        const filteredItems = [];
        if (this.originalItems && this.originalItems.length > 0) {
            this.originalItems.forEach(element => {
                if (element.attributes.workspace_id === this.workspace.id) {
                    filteredItems.push(element);
                }
            });
            this.items = filteredItems;
        }
    }

     // create a new dataset
     createItem() {
        const workspace = this.globalState.getProperty('workspace');
        const params = { 'workspace_id': workspace.id, attributes: {} };
        if (this.newItemTitle) {
            params.attributes['title'] = this.newItemTitle;
        }
        this.apiClient.post(this.baseUrl, params)
            .then((response: any) => {
                // reload
                super.loadItems();
            });
    }
}
