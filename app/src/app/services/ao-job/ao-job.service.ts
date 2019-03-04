import { Injectable } from '@angular/core';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ReplaySubject } from 'rxjs';

@Injectable({
    providedIn: 'root'
})
export class AoJobService {
    static JOB_STATUS_PROCESSING = 'processing';
    static JOB_STATUS_POLL_INTERVAL = 2000;

    constructor(private apiClient: AoApiClientService) { }

    // start polling a job status till its completion
    watchJob(jobId: string): ReplaySubject<any> {
        const notifier = new ReplaySubject();
        this.pollJob(jobId, notifier);
        return notifier;
    }

    // Polls the job status and notify subscribers.
    private pollJob(jobId, notifier: ReplaySubject<any>) {
        this.apiClient.get('/jobs/' + jobId)
            .then((response: any) => {
                // if it is still processing
                if (response.data.attributes.status === AoJobService.JOB_STATUS_PROCESSING) {
                    // retry after a while
                    setTimeout(this.pollJob.bind(this, notifier), AoJobService.JOB_STATUS_POLL_INTERVAL);
                }
                // update subscribers
                notifier.next({ status: response.data.attributes.status, job: response.data });
            })
            .catch((e) => {
                // return exception
                notifier.next({ status: 'exception', exception: e});
            });
    }
}
