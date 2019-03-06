/**
 * Base view for group of objects that are loaded through
 * an API GET call mapping the current URL (e.g. /datasets)
 * Template is delegated to subclasses.
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
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
    urlSubscription: any;
    items: any;
    baseUrl: string;
    queryParamsSubscription: any;
    query: string;

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected itemService: AoItemService) {

    }

    ngOnInit() {
        // take the first url value emitted which will be use as the base url
        this.urlSubscription = this.route.url.pipe(take(1)).subscribe(this.onUrlChange.bind(this));
        this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
            if (this.query !== params.q) {
                this.query = params.q;
                this.refresh();
            }

        });
    }

    ngOnDestroy() {
        if (this.urlSubscription) {
            this.urlSubscription.unsubscribe();
        }
        if (this.queryParamsSubscription) {
            this.queryParamsSubscription.unsubscribe();
        }
    }

    // When id change reload object
    onUrlChange(url: any) {
        this.baseUrl = '/' + url[0].path;
        this.loadItems();
    }

    // loads items
    loadItems() {
        this.apiClient.get(this.baseUrl)
            .then((response: any) => {
                this.items = response.data;
                this.onLoad();
            })
            .catch((response) => {
                if (response.status === 404) {
                    window.location.href = '/app';
                }
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
