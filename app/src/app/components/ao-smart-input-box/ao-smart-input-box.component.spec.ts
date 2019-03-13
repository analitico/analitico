import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoSmartInputBoxComponent } from './ao-smart-input-box.component';

describe('AoSmartInputBoxComponent', () => {
  let component: AoSmartInputBoxComponent;
  let fixture: ComponentFixture<AoSmartInputBoxComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoSmartInputBoxComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoSmartInputBoxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
