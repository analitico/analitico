import { async, ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';

import { AoPipelineViewComponent } from './ao-pipeline-view.component';
import { of } from 'rxjs';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ActivatedRoute } from '@angular/router';
import { MatSnackBarModule } from '@angular/material';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';


// mock ActivateRoute returning url and params
class MockActivatedRoute {
    url = of([{ path: 'dataset' }]);
    params = of({ id: '1' });
}

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

describe('AoPipelineViewComponent', () => {
    let component: AoPipelineViewComponent;
    let fixture: ComponentFixture<AoPipelineViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoPipelineViewComponent, AoAnchorDirective],
            imports: [MatSnackBarModule, BrowserAnimationsModule],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute }
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoPipelineViewComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

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
            expect(component.pluginData.type).toBe('analitico/plugin');
            expect(component.pluginData.name).toBe('analitico.plugin.CsvDataframeSourcePlugin');
        });
    }));
});
