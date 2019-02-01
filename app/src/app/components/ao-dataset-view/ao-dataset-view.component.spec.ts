import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoDatasetViewComponent } from './ao-dataset-view.component';

describe('AoDatasetViewComponent', () => {
  let component: AoDatasetViewComponent;
  let fixture: ComponentFixture<AoDatasetViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoDatasetViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoDatasetViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
