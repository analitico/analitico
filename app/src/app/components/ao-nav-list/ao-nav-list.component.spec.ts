import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { AoNavListComponent } from './ao-nav-list.component';
import { MatListModule } from '@angular/material';

describe('AoNavListComponent', () => {
    let component: AoNavListComponent;
    let fixture: ComponentFixture<AoNavListComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoNavListComponent],
            imports: [MatListModule]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoNavListComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should have <a> with item id', () => {
        component.items = [{
            id: 'id1'
        }];
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const a = list.querySelector('a');
        expect(a.textContent.trim()).toEqual('id1');
    });

    it('should have <a> with item title', () => {
        component.items = [{
            id: 'id1',
            attributes: { title: 'This is the title' }
        }];
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const a = list.querySelector('a');
        expect(a.textContent.trim()).toEqual('This is the title');
    });

    it('should have two <a> with item title', () => {
        component.items = [{
            id: 'id1',
            attributes: { title: 'This is the title' }
        },
        {
            id: 'id2',
            attributes: { title: 'This is the title 2' }
        }];
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const elements = list.querySelectorAll('a');
        expect(elements.length).toEqual(2);
        expect(elements[0].textContent.trim()).toEqual('This is the title');
        expect(elements[1].textContent.trim()).toEqual('This is the title 2');
    });

    it('should filter according to filter property', () => {
        component.items = [{
            id: 'id1',
            attributes: { title: 'This is the title' },
            filter: 1
        },
        {
            id: 'id2',
            attributes: { title: 'This is the title 2' },
            filter: 2
        }];
        component.filter = { filter: 2 };
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const elements = list.querySelectorAll('a');
        expect(elements.length).toEqual(1);
        expect(elements[0].textContent.trim()).toEqual('This is the title 2');
    });

    it('should sort according to sort function', () => {
        component.items = [{
            id: 'id1',
            attributes: { title: 'This is the title' },
            sort: 1
        },
        {
            id: 'id2',
            attributes: { title: 'This is the title 2' },
            sort: 2
        }];
        component.sort = function (a, b) {
            return a.sort > b.sort ? -1 : 1;
        };
        fixture.detectChanges();
        const list: HTMLElement = fixture.nativeElement;
        const elements = list.querySelectorAll('a');
        expect(elements.length).toEqual(2);
        expect(elements[0].textContent.trim()).toEqual('This is the title 2');
        expect(elements[1].textContent.trim()).toEqual('This is the title');
    });
});
