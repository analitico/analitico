import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoDataframePipelinePluginComponent } from './ao-dataframe-pipeline-plugin.component';

describe('AoDataframePipelinePluginComponent', () => {
  let component: AoDataframePipelinePluginComponent;
  let fixture: ComponentFixture<AoDataframePipelinePluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoDataframePipelinePluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoDataframePipelinePluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
