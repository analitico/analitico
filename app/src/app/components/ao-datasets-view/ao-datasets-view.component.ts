import { Component, OnInit } from '@angular/core';
import { AoGroupWsViewComponent } from 'src/app/components/ao-group-ws-view/ao-group-ws-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';

@Component({
    selector: 'app-ao-datasets-view',
    templateUrl: './ao-datasets-view.component.html',
    styleUrls: ['./ao-datasets-view.component.css']
})
export class AoDatasetsViewComponent extends AoGroupWsViewComponent implements OnInit {

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore) {
        super(route, apiClient, globalState);
    }

    ngOnInit() {
        super.ngOnInit();
    }

    onLoad() {
        // look at workspace and filter
        super.onLoad();
    }
}
