import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoNavListComponent } from './ao-nav-list.component';

describe('AoNavListComponent', () => {
  let component: AoNavListComponent;
  let fixture: ComponentFixture<AoNavListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoNavListComponent ]
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
});
