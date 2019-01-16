import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoLoginComponent } from './ao-login.component';

describe('AoLoginComponent', () => {
  let component: AoLoginComponent;
  let fixture: ComponentFixture<AoLoginComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoLoginComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoLoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
