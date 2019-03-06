/**
 * Summary view for Trained models
 */
import { Component, OnInit } from '@angular/core';
import { AoGroupWsViewComponent } from '../ao-group-ws-view/ao-group-ws-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';


@Component({
    selector: 'app-ao-models-view',
    templateUrl: './ao-models-view.component.html',
    styleUrls: ['./ao-models-view.component.css']
})
export class AoModelsViewComponent extends AoGroupWsViewComponent implements OnInit {

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore, protected router: Router,
        protected itemService: AoItemService) {
        super(route, apiClient, globalState, router, itemService);
    }

    ngOnInit() {
        super.ngOnInit();
        this.displayedColumns = ['attributes.title', 'attributes.recipe_id', 'attributes.updated_at',
            'attributes.training.scores.best_score.learn.RMSE', 'endpoint', 'actions'];
    }

    // loads items
    loadItems() {
        this.itemService.getModels()
            .then((models: any) => {
                this.items = models;
                this.onLoad();
            })
            .catch((response) => {
                if (response.status === 404) {
                    window.location.href = '/app';
                }
            });
    }

    onLoad() {
        // look at workspace and filter
        super.onLoad();

    }
}
