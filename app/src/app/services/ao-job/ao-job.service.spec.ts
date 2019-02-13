import { TestBed } from '@angular/core/testing';

import { AoJobService } from './ao-job.service';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';


class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: {
                    attributes: {
                        status: 'done'
                    }
                }
            });
        });

    }
}

describe('AoJobService', () => {
    beforeEach(() => TestBed.configureTestingModule({
        providers: [
            { provide: AoApiClientService, useClass: MockAoApiClientService }
        ]
    }));

    it('should be created', () => {
        const service: AoJobService = TestBed.get(AoJobService);
        expect(service).toBeTruthy();
    });

    it('should poll job', (done) => {
        const service: AoJobService = TestBed.get(AoJobService);
        service.watchJob('123').subscribe({
            next(data: any) {
                if (data.status === 'done') {
                    done();
                }
            }
        });
    });
});
