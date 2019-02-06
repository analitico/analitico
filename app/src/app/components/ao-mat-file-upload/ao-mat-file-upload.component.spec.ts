import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoMatFileUploadComponent } from './ao-mat-file-upload.component';

describe('AoMatFileUploadComponent', () => {
  let component: AoMatFileUploadComponent;
  let fixture: ComponentFixture<AoMatFileUploadComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoMatFileUploadComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoMatFileUploadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
