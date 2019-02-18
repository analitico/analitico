import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoModelsViewComponent } from './ao-models-view.component';
import { MatGridListModule } from '@angular/material';
import { RouterTestingModule } from '@angular/router/testing';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ActivatedRoute } from '@angular/router';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';


class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: [
                    {
                        id: 'id1',
                        attributes: {
                            workspace: 'ws1'
                        }
                    },
                    {
                        id: 'id2',
                        attributes: {
                            workspace: 'ws2'
                        }
                    }
                ]
            });
        });
    }
}

class MockActivatedRoute {
    url = of([{ path: 'models' }]).pipe(delay(100));
}
class MockGlobalStateStore {
    subscribe(fn: any) {
        setTimeout(fn, 100);
        // call the subscribers async
        return {
            unsubscribe: function () { }
        };
    }

    getProperty() {
        // return fake workspace
        return { id: 'ws1' };
    }

}


describe('AoModelsViewComponent', () => {
    let component: AoModelsViewComponent;
    let fixture: ComponentFixture<AoModelsViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoModelsViewComponent],
            imports: [RouterTestingModule, MatGridListModule],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute },
                { provide: AoGlobalStateStore, useClass: MockGlobalStateStore }
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoModelsViewComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
