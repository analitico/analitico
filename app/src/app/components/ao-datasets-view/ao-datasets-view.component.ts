import { Component, OnInit } from '@angular/core';
import { AoGroupWsViewComponent } from 'src/app/components/ao-group-ws-view/ao-group-ws-view.component';
import { ActivatedRoute, Router } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-datasets-view',
    templateUrl: './ao-datasets-view.component.html',
    styleUrls: ['./ao-datasets-view.component.css']
})
export class AoDatasetsViewComponent extends AoGroupWsViewComponent implements OnInit {

    displayedColumns: string[] = ['attributes.title', 'attributes.updated_at', 'actions'];

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore, protected jobService: AoJobService, protected router: Router,
        protected itemService: AoItemService) {
        super(route, apiClient, globalState, router, itemService);
    }

    ngOnInit() {
        super.ngOnInit();
    }

    onLoad() {
        // look at workspace and filter
        super.onLoad();
    }

    process(dataset, $event) {
        $event.preventDefault();
        $event.stopPropagation();
        if (dataset.isProcessing) {
            return;
        }
        dataset.isProcessing = true;
        const that = this;
        return this.itemService.processDataset(dataset.id)
            .then((emitter: any) => {
                emitter.subscribe({
                    next(data: any) {
                        if (data.status !== 'processing') {
                            dataset.isProcessing = false;
                            // refresh UI
                            that.refresh();
                        }
                    }
                });
            })
            .catch(() => {
                dataset.isProcessing = false;
            });


    }
}
