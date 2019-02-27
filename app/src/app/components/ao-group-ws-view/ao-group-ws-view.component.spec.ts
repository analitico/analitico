import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGroupWsViewComponent } from './ao-group-ws-view.component';
import { delay } from 'rxjs/operators';
import { of } from 'rxjs';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { FormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { MatCardModule, MatListModule, MatTableModule, MatFormField, MatFormFieldModule, MatInputModule } from '@angular/material';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: [
                    {
                        id: 'id1',
                        attributes: {
                            workspace_id: 'ws1'
                        }
                    },
                    {
                        id: 'id2',
                        attributes: {
                            workspace_id: 'ws2'
                        }
                    }
                ]
            });
        });
    }
}

// mock ActivateRoute returning url and params
class MockActivatedRoute {
    url = of([{ path: 'datasets' }]).pipe(delay(100));
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

describe('AoGroupWsViewComponent', () => {
    let component: AoGroupWsViewComponent;
    let fixture: ComponentFixture<AoGroupWsViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoGroupWsViewComponent],
            imports: [FormsModule, RouterTestingModule, MatListModule, MatCardModule, MatTableModule, MatInputModule, NoopAnimationsModule],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute },
                { provide: AoGlobalStateStore, useClass: MockGlobalStateStore }]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoGroupWsViewComponent);
        component = fixture.componentInstance;
    });

    it('should create', () => {
        fixture.detectChanges();
        expect(component).toBeTruthy();
    });

    it('should load 1 items', async(() => {
        fixture.detectChanges();
        fixture.whenStable().then(() => {
            fixture.detectChanges();
            expect(component.items.length).toEqual(1);
            expect(component.items[0].attributes.workspace_id).toEqual('ws1');
        });
    }));

});
