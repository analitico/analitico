import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoViewComponent } from './ao-view.component';

describe('AoViewComponent', () => {
  let component: AoViewComponent;
  let fixture: ComponentFixture<AoViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
