import { async, ComponentFixture, TestBed} from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoGroupViewComponent } from './ao-group-view.component';
import { delay } from 'rxjs/operators';
import { of } from 'rxjs';

class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: [
                    {
                        id: 'id1'
                    },
                    {
                        id: 'id2'
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

describe('AoGroupViewComponent', () => {
    let component: AoGroupViewComponent;
    let fixture: ComponentFixture<AoGroupViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoGroupViewComponent],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute }]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoGroupViewComponent);
        component = fixture.componentInstance;
    });

    it('should create', () => {
        fixture.detectChanges();
        expect(component).toBeTruthy();
    });

    it('should load 2 items', async(() => {
        fixture.detectChanges();
        fixture.whenStable().then(() => {
            fixture.detectChanges();
            expect(component.items.length).toEqual(2);
        });
    }));

});
