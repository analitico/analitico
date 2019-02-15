import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoTableViewComponent } from './ao-table-view.component';

describe('AoTableViewComponent', () => {
  let component: AoTableViewComponent;
  let fixture: ComponentFixture<AoTableViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoTableViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoTableViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
