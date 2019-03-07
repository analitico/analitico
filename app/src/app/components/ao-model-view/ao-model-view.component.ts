/**
 * Model represents a trained model that can be associated with an endpoint to be consumed
 */
import { Component, OnInit } from '@angular/core';
import { AoViewComponent } from 'src/app/components/ao-view/ao-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { MatTableDataSource } from '@angular/material';


@Component({
    templateUrl: './ao-model-view.component.html',
    styleUrls: ['./ao-model-view.component.css']
})
export class AoModelViewComponent extends AoViewComponent implements OnInit {
    recipe: any;
    tableModels: any;
    alternativeModels: any;


    constructor(route: ActivatedRoute, apiClient: AoApiClientService,
        protected snackBar: MatSnackBar,
        protected itemService: AoItemService,
        protected router: Router) {
        super(route, apiClient, itemService, snackBar);
    }

    ngOnInit() {
        super.ngOnInit();
    }

    /**
     * override method
     */
    loadItem() {
        return this.itemService.getModelById(this.objectId)
            .then((model: any) => {
                this.item = model;
                this.recipe = this.item._aoprivate.recipe;
                this.title = (this.item.attributes && this.item.attributes.title) || this.item.id;
                this.description = this.item.description;
                this.alternativeModels = [];
                this.onLoad();
            })
            .catch((response) => {
                if (response.status === 404) {
                    window.location.href = '/app';
                }
            });
    }

    // find models with the same recipe_id for switching
    loadAlternativeModels() {
        this.itemService.getModels()
            .then((models) => {
                this.alternativeModels = [];
                models.forEach(model => {
                    if (model.attributes.recipe_id === this.item.attributes.recipe_id) {

                        this.alternativeModels.push(model);

                    }
                });

                // assign data source for the table
                this.tableModels = new MatTableDataSource(this.alternativeModels);

            });
    }

    onLoad() {
        super.onLoad();
        this.loadAlternativeModels();
    }


    onSaved() {
        // show a message
        this.snackBar.open('Item has been saved', null, { duration: 3000 });
    }

    createEndpointForModel(model) {
        this.itemService.createEndpointForModel(model)
            .then((endpoint) => {
                // open the endpoint page
                this.router.navigate(['/endpoints/' + endpoint.id]);
            });

    }
}
