import { async, ComponentFixture, TestBed, fakeAsync, tick, flushMicrotasks } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AoDatasetViewComponent } from './ao-dataset-view.component';
import {
    MatSidenavModule, MatProgressSpinnerModule, MatIconModule, MatListModule, MatSnackBarModule
} from '@angular/material';
import { AoMatFileUploadQueueComponent } from 'src/app/components/ao-mat-file-upload-queue/ao-mat-file-upload-queue.component';
import { AoFileUploadInputForDirective } from 'src/app/directives/ao-file-upload-input-for/ao-file-upload-input-for.directive';
import { AoNavListComponent } from 'src/app/components/ao-nav-list/ao-nav-list.component';
import { AoMatFileUploadComponent } from 'src/app/components/ao-mat-file-upload/ao-mat-file-upload.component';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ActivatedRoute } from '@angular/router';
import { delay } from 'rxjs/operators';
import { of } from 'rxjs';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { environment } from '../../../environments/environment';

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
    url = of([{ path: 'dataset' }]);
    params = of({ id: '1' });
}

describe('AoDatasetViewComponent', () => {
    let component: AoDatasetViewComponent;
    let fixture: ComponentFixture<AoDatasetViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoDatasetViewComponent, AoMatFileUploadQueueComponent, AoFileUploadInputForDirective,
                AoNavListComponent, AoMatFileUploadComponent, AoAnchorDirective],
            imports: [MatProgressSpinnerModule, MatSidenavModule, MatIconModule, MatListModule, MatSnackBarModule, BrowserAnimationsModule],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute }
            ]

        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoDatasetViewComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    /* it('should create', () => {
         expect(component).toBeTruthy();
     }); */

    it('should set object id', fakeAsync(() => {
        fixture.detectChanges();
        tick(10000);
        fixture.detectChanges();
        expect(component.objectId).toEqual('1');
    }));

    it('should load item', async(() => {
        fixture.detectChanges();
        component.objectId = '1';
        component.loadItem();
        fixture.whenStable().then(() => {
            fixture.detectChanges();
            expect(component.title).toBe('1');
            expect(component.uploadAssetUrl).toBe(environment.apiUrl + '/datasets/1/assets');
            expect(component.pluginData.type).toBe('analitico/plugin');
            expect(component.pluginData.name).toBe( 'analitico.plugin.CsvDataframeSourcePlugin');
        });
    }));
});
