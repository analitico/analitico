/**
 * Model represents a trained model that can be associated with an endpoint to be consumed
 */
import { Component, OnInit } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';


@Component({
    templateUrl: './ao-model-view.component.html',
    styleUrls: ['./ao-model-view.component.css']
})
export class AoModelViewComponent extends AoViewComponent implements OnInit {

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        private snackBar: MatSnackBar,
        protected itemService: AoItemService) {
        super(route, apiClient, itemService);
    }

    ngOnInit() {
        super.ngOnInit();
    }

    onLoad() {
        super.onLoad();
    }


    onSaved() {
        // show a message
        this.snackBar.open('Item has been saved', null, { duration: 3000 });
    }

}
