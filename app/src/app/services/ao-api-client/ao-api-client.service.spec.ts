import { TestBed } from '@angular/core/testing';

import { AoApiClientService } from './ao-api-client.service';
import { HttpClientModule } from '@angular/common/http';

describe('AoApiClientService', () => {
    beforeEach(() => TestBed.configureTestingModule({
        providers: [AoApiClientService],
        imports: [HttpClientModule]
    }));

    it('should be created', () => {
        const service: AoApiClientService = TestBed.get(AoApiClientService);
        expect(service).toBeTruthy();
    });

    it('should get data', (done) => {
        const service: AoApiClientService = TestBed.get(AoApiClientService);
        service.get('http://localhost:3000/author')
            .then((data: any) => {
                expect(data.length === 2);
                done();
            })
            .catch((error: any) => {
                throw new Error(error);
            })
            .finally(done);
    });
});
