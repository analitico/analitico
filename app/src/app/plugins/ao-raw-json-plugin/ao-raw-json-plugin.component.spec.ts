import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoRawJsonPluginComponent } from './ao-raw-json-plugin.component';
import { JsonEditorComponent, JsonEditorOptions } from 'ang-jsoneditor';
import {
    MatCardModule
} from '@angular/material';
describe('AoRawJsonPluginComponent', () => {
  let component: AoRawJsonPluginComponent;
  let fixture: ComponentFixture<AoRawJsonPluginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoRawJsonPluginComponent, JsonEditorComponent ],
      imports: [MatCardModule]
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
