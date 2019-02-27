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
                    id: 'id1',
                    attributes: {
                        title: 'Title id 1'
                    }
                },
                {
                    id: 'id2',
                    attributes: {
                        title: 'Title id 2'
                    }
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

    it('should have elements', fakeAsync(() => {
        component.title = 'Dataset';
        component.url = 'myurl';
        tick();
        fixture.detectChanges();
        const ne: HTMLElement = fixture.nativeElement;
        const titleElement = ne.querySelector('.ao-nav-list-item span');
        expect(titleElement.textContent.trim()).toEqual('Dataset');
        const children = ne.querySelectorAll('.ao-nav-list-children .ao-nav-list-item');
        expect(children.length).toBe(2);
        expect(children[0].textContent.trim()).toBe('Title id 1');
        expect(children[1].textContent.trim()).toBe('Title id 2');
    }));
});
