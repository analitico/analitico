import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoNavListFromUrlComponent } from './ao-nav-list-from-url.component';

describe('AoNavListFromUrlComponent', () => {
  let component: AoNavListFromUrlComponent;
  let fixture: ComponentFixture<AoNavListFromUrlComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoNavListFromUrlComponent ]
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
});
