import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoCsvDataframeSourcePluginComponent } from './ao-csv-dataframe-source-plugin.component';

describe('AoCsvDataframeSourcePluginComponent', () => {
  let component: AoCsvDataframeSourcePluginComponent;
  let fixture: ComponentFixture<AoCsvDataframeSourcePluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoCsvDataframeSourcePluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoCsvDataframeSourcePluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
