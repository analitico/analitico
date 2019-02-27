import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoPipelinePluginComponent } from './ao-pipeline-plugin.component';

describe('AoPipelinePluginComponent', () => {
  let component: AoPipelinePluginComponent;
  let fixture: ComponentFixture<AoPipelinePluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoPipelinePluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoPipelinePluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
