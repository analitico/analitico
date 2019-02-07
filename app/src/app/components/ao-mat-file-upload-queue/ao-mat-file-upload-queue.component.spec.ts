import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoMatFileUploadQueueComponent } from './ao-mat-file-upload-queue.component';

describe('AoMatFileUploadQueueComponent', () => {
  let component: AoMatFileUploadQueueComponent;
  let fixture: ComponentFixture<AoMatFileUploadQueueComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoMatFileUploadQueueComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoMatFileUploadQueueComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
