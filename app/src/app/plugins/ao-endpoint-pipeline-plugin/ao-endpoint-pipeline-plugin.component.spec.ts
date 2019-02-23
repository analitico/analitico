import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoEndpointPipelinePluginComponent } from './ao-endpoint-pipeline-plugin.component';

describe('AoEndpointPipelinePluginComponent', () => {
  let component: AoEndpointPipelinePluginComponent;
  let fixture: ComponentFixture<AoEndpointPipelinePluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoEndpointPipelinePluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoEndpointPipelinePluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
