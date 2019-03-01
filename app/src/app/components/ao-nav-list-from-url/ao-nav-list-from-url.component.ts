/**
 * A nav-list "Google Drive style" component that load object list from a url
 */
import { Component, OnInit, Input } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoNavListComponent } from 'src/app/components/ao-nav-list/ao-nav-list.component';
import { Router } from '@angular/router';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-nav-list-from-url',
    templateUrl: './ao-nav-list-from-url.component.html',
    styleUrls: ['./ao-nav-list-from-url.component.css']
})
export class AoNavListFromUrlComponent extends AoNavListComponent implements OnInit {

    constructor(protected apiClient: AoApiClientService, private router: Router, protected itemService: AoItemService) {
        super(itemService);
        this.isCollapsed = true;
    }

    private _url: any;
    get url() {
        return this._url;
    }
    @Input() set url(val: string) {
        if (val) {
            this._url = val;
            this.loadlistIfNotCollapsed();
        }
    }
    @Input() set filter(val: any) {
        if (val) {
            this._filter = val;
            this.loadlistIfNotCollapsed();
        }
    }
    @Input() set sort(val: any) {
        if (val) {
            this._sortFunction = val;
            this.loadlistIfNotCollapsed();
        }
    }

    @Input() newItemParams: any;
    @Input() allowItemCreation = true;
    isCollapsed: any;
    @Input() icon: string;

    ngOnInit() {
    }

    loadlistIfNotCollapsed() {
        if (!this.isCollapsed) {
            this.loadListFromUrl();
        }
    }

    // loads an url  that provides a list of objects with id and title properties
    loadListFromUrl() {
        this._items = [];
        if (this._url) {
            this.apiClient.get(this._url)
                .then((response: any) => {
                    this.items = response.data;
                    this.processItems();
                });
        }
    }

    createNewItem() {
        this.apiClient.post(this._url, this.newItemParams)
            .then((response: any) => {
                // refresh list
                this.loadListFromUrl();
                this.router.navigate([this._url + '/' + response.data.id]);
            });
    }

    // delete an item using DELETE request
    deleteItem(item: any) {
        this.apiClient.delete(this._url + '/' + item.id)
            .then((response: any) => {
                this.loadListFromUrl();
            });
    }

    toggleList($event) {
        $event.stopPropagation();
        $event.preventDefault();
        if (this.isCollapsed) {
            // reload
            this.loadListFromUrl();
        }
        this.isCollapsed = !this.isCollapsed;
    }

}
