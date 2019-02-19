import { async, fakeAsync, tick, ComponentFixture, TestBed } from '@angular/core/testing';
import { MatListModule, MatIconModule } from '@angular/material';
import { AoNavListFromUrlComponent } from './ao-nav-list-from-url.component';
import { RouterModule } from '@angular/router';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { RouterTestingModule } from '@angular/router/testing';

class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: [{
                    id: 'id1'
                }]
            });
        });

    }
    delete(url: string) {
        return {};
    }
}

describe('AoNavListFromUrlComponent', () => {
    let component: AoNavListFromUrlComponent;
    let fixture: ComponentFixture<AoNavListFromUrlComponent>;


    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoNavListFromUrlComponent],
            imports: [MatListModule, RouterModule, MatIconModule, RouterTestingModule],
            providers: [{ provide: AoApiClientService, useClass: MockAoApiClientService }]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoNavListFromUrlComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should have <a> with item id', fakeAsync(() => {
        component.url = 'myurl';
        tick();
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const a = list.querySelector('.ao-nav-list-item');
        expect(a.textContent.trim()).toEqual('id1');
    }));
});
