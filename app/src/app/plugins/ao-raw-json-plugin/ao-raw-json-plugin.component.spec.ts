import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoRawJsonPluginComponent } from './ao-raw-json-plugin.component';

describe('AoRawJsonPluginComponent', () => {
  let component: AoRawJsonPluginComponent;
  let fixture: ComponentFixture<AoRawJsonPluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoRawJsonPluginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoRawJsonPluginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
