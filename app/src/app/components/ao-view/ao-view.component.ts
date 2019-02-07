/**
 * Base view class loads a json object using a GET call to the API url that match the current browser path
 * (e.g., /datasets/ds_test).
 * It allows to store back the object using a PATCH call to the same API.
 * Template is delegated to subclasses
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { take } from 'rxjs/operators';

@Component({
    selector: 'app-ao-view',
    templateUrl: './ao-view.component.html',
    styleUrls: ['./ao-view.component.css']
})
export class AoViewComponent implements OnInit, OnDestroy {
    urlSubscription: any;
    activatedRouteSubscription: any;
    objectId: string;
    item: any;
    baseUrl: string;

    constructor(private route: ActivatedRoute, protected apiClient: AoApiClientService) {

    }

    ngOnInit() {
        // take the first url value emitted which will be use as the base url
        this.urlSubscription = this.route.url.pipe(take(1)).subscribe(this.onUrlChange.bind(this));
    }

    ngOnDestroy() {
        if (this.urlSubscription) {
            this.urlSubscription.unsubscribe();
        }
        // unsubscribe to avoid memory leaks
        if (this.activatedRouteSubscription) {
            this.activatedRouteSubscription.unsubscribe();
        }
    }

    // When id change reload object
    onUrlChange(url: any) {
        this.baseUrl = '/' + url[0].path;
        // listen to id change
        this.activatedRouteSubscription = this.route.params.subscribe(this.onRouteChange.bind(this));
    }

    // When id change reload object
    onRouteChange(params: any) {
        if (!this.objectId || this.objectId !== params.id) {
            this.objectId = params.id;
            console.log('loading ' + this.objectId);
            this.loadItem();
        }
    }

    // loads the json object
    loadItem() {
        this.apiClient.get(this.baseUrl + '/' + this.objectId)
            .then((response: any) => {
                this.item = response.data;
                this.onLoad();
            })
            .catch((response) => {
                /*if (response.status === 404) {
                    window.location.href = this.baseUrl;
                }*/
            });
    }

    saveItem() {
        const that = this;
        return new Promise(function (resolve, reject) {
            if (!that.item) {
                reject(new Error('missing item'));
            }
            that.apiClient.patch(that.baseUrl + '/' + that.item.id, that.item)
                .then((response: any) => {
                    that.item = response.data;
                    that.onSaved();
                    resolve(response.data);
                    // refresh
                    // this.onLoad();
                })
                .catch(reject);
        });

    }

    onLoad(): void { }

    onSaved(): void { }
}
