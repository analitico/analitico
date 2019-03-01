import { TestBed } from '@angular/core/testing';

import { AoApiClientService } from './ao-api-client.service';
import { HttpClientModule } from '@angular/common/http';
import { MatDialogModule, MatCardModule, MatButtonModule, MatToolbar } from '@angular/material';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AoDialogComponent } from 'src/app/components/ao-dialog/ao-dialog.component';
import { AoMessageBoxService } from '../ao-message-box/ao-message-box';

describe('AoApiClientService', () => {
    beforeEach(() => TestBed.configureTestingModule({
        providers: [AoApiClientService, AoMessageBoxService, AoDialogComponent],
        declarations: [AoDialogComponent, MatToolbar],
        imports: [HttpClientModule, MatDialogModule, NoopAnimationsModule, MatCardModule, MatButtonModule]
    }));

    it('should be created', () => {
        const service: AoApiClientService = TestBed.get(AoApiClientService);
        expect(service).toBeTruthy();
    });

    it('should get data', (done) => {
        const service: AoApiClientService = TestBed.get(AoApiClientService);
        service.get('../../api.test.json')
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
