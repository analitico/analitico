import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoRecipePipelinePluginComponent } from './ao-recipe-pipeline-plugin.component';

describe('AoRecipePipelinePluginComponent', () => {
  let component: AoRecipePipelinePluginComponent;
  let fixture: ComponentFixture<AoRecipePipelinePluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoRecipePipelinePluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoRecipePipelinePluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
