import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoLoginComponent } from './ao-login.component';

import { MatCardModule, MatInputModule } from '@angular/material';

import { FormsModule } from '@angular/forms';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { HttpClientModule } from '@angular/common/http';

describe('AoLoginComponent', () => {
    let component: AoLoginComponent;
    let fixture: ComponentFixture<AoLoginComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoLoginComponent],
            imports: [ MatCardModule, MatInputModule, FormsModule, BrowserAnimationsModule, HttpClientModule ],
            providers: [AoGlobalStateStore, AoApiClientService]
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
