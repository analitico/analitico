import { Component, OnInit, Input } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    selector: 'app-ao-nav-list',
    templateUrl: './ao-nav-list.component.html',
    styleUrls: ['./ao-nav-list.component.css']
})
export class AoNavListComponent implements OnInit {
    @Input() url: string;
    @Input() title: string;
    items: any;

    constructor(private apiClient: AoApiClientService) { }

    ngOnInit() {
        this.loadListFromUrl();
    }

    // loads an url  that provides a list of objects with id and title properties
    loadListFromUrl() {
        this.apiClient.get(this.url)
            .then((response: any) => {
                this.items = response.data;
            });
    }

}
