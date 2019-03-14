/**
 * Base view for group of objects that are loaded through
 * an API GET call mapping the current URL (e.g. /datasets)
 * Template is delegated to subclasses.
 */

import { Component, OnInit, OnDestroy, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { take } from 'rxjs/operators';
import { AoRefreshable } from 'src/app/ao-refreshable';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-group-view',
    templateUrl: './ao-group-view.component.html',
    styleUrls: ['./ao-group-view.component.css']
})
export class AoGroupViewComponent implements OnInit, OnDestroy, AoRefreshable {
    items: any;
    baseUrl: string;
    queryParamsSubscription: any;
    query: string;

    private _url: any;
    get url() {
        return this._url;
    }
    @Input() set url(val: string) {
        if (val) {
            this._url = val;
            this.loadItems();
        }
    }

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected itemService: AoItemService) {

    }

    ngOnInit() {
        this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
            if (this.query !== params.q) {
                this.query = params.q;
                this.refresh();
            }
        });
    }

    ngOnDestroy() {
        if (this.queryParamsSubscription) {
            this.queryParamsSubscription.unsubscribe();
        }
    }


    // loads items
    loadItems() {
        this.apiClient.get(this.url)
            .then((response: any) => {
                this.items = response.data;
                this.onLoad();
            });
    }

    onLoad(): void {
        if (this.query) {
            this.items = this.itemService.filterItemsByString(this.items, this.query);
        }
    }


    refresh() {
        this.loadItems();
    }
}
