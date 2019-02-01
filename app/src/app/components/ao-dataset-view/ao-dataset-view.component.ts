import { Component, OnInit, OnDestroy } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    templateUrl: './ao-dataset-view.component.html',
    styleUrls: ['./ao-dataset-view.component.css']
})
export class AoDatasetViewComponent extends AoViewComponent implements OnInit {

    constructor(route: ActivatedRoute, apiClient: AoApiClientService) {
        super(route, apiClient);
    }

    ngOnInit() {
        super.ngOnInit();
    }


}
