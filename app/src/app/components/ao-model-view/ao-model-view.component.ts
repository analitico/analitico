/**
 * Model represents a trained model that can be associated with an endpoint to be consumed
 */
import { Component, OnInit } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { MatSnackBar } from '@angular/material/snack-bar';


@Component({
    templateUrl: './ao-model-view.component.html',
    styleUrls: ['./ao-model-view.component.css']
})
export class AoModelViewComponent extends AoViewComponent implements OnInit {

    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        private snackBar: MatSnackBar) {
        super(route, apiClient);
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
