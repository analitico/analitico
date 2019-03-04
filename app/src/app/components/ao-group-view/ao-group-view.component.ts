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

@Component({
    selector: 'app-ao-group-view',
    templateUrl: './ao-group-view.component.html',
    styleUrls: ['./ao-group-view.component.css']
})
export class AoGroupViewComponent implements OnInit, OnDestroy, AoRefreshable {
    urlSubscription: any;
    items: any;
    baseUrl: string;

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService) {

    }

    ngOnInit() {
        // take the first url value emitted which will be use as the base url
        this.urlSubscription = this.route.url.pipe(take(1)).subscribe(this.onUrlChange.bind(this));
    }

    ngOnDestroy() {
        if (this.urlSubscription) {
            this.urlSubscription.unsubscribe();
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

    onLoad(): void { }


    refresh() {
        this.loadItems();
    }
}
