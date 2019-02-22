import { Component, OnInit } from '@angular/core';
import { AoGroupWsViewComponent } from 'src/app/components/ao-group-ws-view/ao-group-ws-view.component';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoJobService } from 'src/app/services/ao-job/ao-job.service';

@Component({
    selector: 'app-ao-datasets-view',
    templateUrl: './ao-datasets-view.component.html',
    styleUrls: ['./ao-datasets-view.component.css']
})
export class AoDatasetsViewComponent extends AoGroupWsViewComponent implements OnInit {

    displayedColumns: string[] = ['id', 'attributes.title', 'attributes.created_at', 'actions'];

    constructor(protected route: ActivatedRoute, protected apiClient: AoApiClientService,
        protected globalState: AoGlobalStateStore, private jobService: AoJobService) {
        super(route, apiClient, globalState);
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
        this.apiClient.post('/datasets/' + dataset.id + '/data/process', {})
            .then((response: any) => {
                const jobId = response.data.id;
                // set a watcher for this job
                this.jobService.watchJob(jobId)
                    .subscribe({
                        next(data: any) {
                            if (data.status !== 'processing') {
                                dataset.isProcessing = false;
                            }
                        }
                    });
            })
            .catch(() => {
                dataset.isProcessing = false;
            });
    }
}
