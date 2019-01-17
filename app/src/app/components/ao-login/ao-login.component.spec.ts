import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoLoginComponent } from './ao-login.component';

import { MatCardModule, MatInputModule } from '@angular/material';

import { FormsModule } from '@angular/forms';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('AoLoginComponent', () => {
    let component: AoLoginComponent;
    let fixture: ComponentFixture<AoLoginComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoLoginComponent],
            imports: [ MatCardModule, MatInputModule, FormsModule, BrowserAnimationsModule ]
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
