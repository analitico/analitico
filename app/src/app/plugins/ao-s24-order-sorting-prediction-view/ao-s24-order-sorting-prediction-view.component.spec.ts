import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoS24OrderSortingPredictionViewComponent } from './ao-s24-order-sorting-prediction-view.component';

describe('AoS24OrderSortingPredictionViewComponent', () => {
  let component: AoS24OrderSortingPredictionViewComponent;
  let fixture: ComponentFixture<AoS24OrderSortingPredictionViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoS24OrderSortingPredictionViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoS24OrderSortingPredictionViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
