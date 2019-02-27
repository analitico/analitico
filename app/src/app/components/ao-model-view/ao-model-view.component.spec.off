import { async, ComponentFixture, TestBed, fakeAsync, tick, flushMicrotasks } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AoModelViewComponent } from './ao-model-view.component';
import {
    MatSidenavModule, MatProgressSpinnerModule, MatIconModule, MatListModule, MatSnackBarModule, MatCardModule
} from '@angular/material';
import { AoMatFileUploadQueueComponent } from 'src/app/components/ao-mat-file-upload-queue/ao-mat-file-upload-queue.component';
import { AoFileUploadInputForDirective } from 'src/app/directives/ao-file-upload-input-for/ao-file-upload-input-for.directive';
import { AoNavListComponent } from 'src/app/components/ao-nav-list/ao-nav-list.component';
import { AoMatFileUploadComponent } from 'src/app/components/ao-mat-file-upload/ao-mat-file-upload.component';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ActivatedRoute } from '@angular/router';

import { of } from 'rxjs';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';

import { AoTableViewComponent } from '../ao-table-view/ao-table-view.component';


class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: {
                    id: '1',
                    attributes: {
                        'plugin': {
                            'type': 'analitico/plugin',
                            'name': 'analitico.plugin.CsvDataframeSourcePlugin'
                        }
                    }
                }
            });
        });

    }
}

// mock ActivateRoute returning url and params
class MockActivatedRoute {
    url = of([{ path: 'models' }]);
    params = of({ id: '1' });
}

describe('AoModelViewComponent', () => {
    let component: AoModelViewComponent;
    let fixture: ComponentFixture<AoModelViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoModelViewComponent, AoMatFileUploadQueueComponent, AoFileUploadInputForDirective,
                AoNavListComponent, AoMatFileUploadComponent, AoAnchorDirective, AoTableViewComponent],
            imports: [MatProgressSpinnerModule, MatSidenavModule, MatIconModule, MatListModule, MatCardModule,
                MatSnackBarModule, BrowserAnimationsModule],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute }
            ]

        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoModelViewComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });
});
