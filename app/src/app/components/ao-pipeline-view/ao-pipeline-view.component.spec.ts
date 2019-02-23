import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoPipelineViewComponent } from './ao-pipeline-view.component';

describe('AoPipelineViewComponent', () => {
  let component: AoPipelineViewComponent;
  let fixture: ComponentFixture<AoPipelineViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoPipelineViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoPipelineViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
