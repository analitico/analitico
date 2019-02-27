import { async, ComponentFixture, TestBed, tick, fakeAsync, } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { AoViewComponent } from './ao-view.component';
import { delay, concatMap } from 'rxjs/operators';
import { of, from } from 'rxjs';

class MockAoApiClientService {
    data =  {
        id: 'id1'
    };
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: this.data
            });
        });

    }
    patch(url: string) {
        this.data['saved'] = true;
        return new Promise((resolve, reject) => {
            resolve({
                data: this.data
            });
        });
    }
}

// mock ActivateRoute returning url and params
class MockActivatedRoute {
    url = of([{ path: 'dataset' }]).pipe(delay(100));
    params = from([{id: '1'}, {id: '2'}]).pipe(
        concatMap(item => of(item).pipe(delay(1000)))
    );
}

describe('AoViewComponent', () => {
    let component: AoViewComponent;
    let fixture: ComponentFixture<AoViewComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoViewComponent],
            providers: [
                { provide: AoApiClientService, useClass: MockAoApiClientService },
                { provide: ActivatedRoute, useClass: MockActivatedRoute }]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoViewComponent);
        component = fixture.componentInstance;
    });

    it('should create', () => {
        fixture.detectChanges();
        expect(component).toBeTruthy();
    });

    it('should get url path and object id', fakeAsync(() => {
        const spy = spyOn(component, 'onLoad');
        fixture.detectChanges();
        tick(1850);
        fixture.detectChanges();
        expect(component.baseUrl).toEqual('/dataset');
        expect(component.objectId).toEqual('1');
        expect(spy).toHaveBeenCalled();
        tick(1850);
        fixture.detectChanges();
        expect(component.objectId).toEqual('2');
        expect(spy).toHaveBeenCalled();
    }));

    it('should save item', fakeAsync(() => {
        const spy = spyOn(component, 'onSaved');
        fixture.detectChanges();
        tick(3000);
        fixture.detectChanges();
        expect(component.objectId).toEqual('2');
        // save
        component.saveItem();
        tick(1000);
        fixture.detectChanges();
        expect(spy).toHaveBeenCalled();
        component.loadItem();
        tick(1000);
        fixture.detectChanges();
        expect(component.objectId).toEqual('2');
        expect(component.item.saved).toBeTruthy();
    }));
});
