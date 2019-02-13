import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoMatFileUploadComponent } from './ao-mat-file-upload.component';
import {
    MatIconModule, MatProgressSpinnerModule
} from '@angular/material';
import { HttpClient } from '@angular/common/http';

class MockHttpClient {

}

describe('AoMatFileUploadComponent', () => {
    let component: AoMatFileUploadComponent;
    let fixture: ComponentFixture<AoMatFileUploadComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoMatFileUploadComponent],
            imports: [
                MatProgressSpinnerModule,
                MatIconModule
            ],
            providers: [
                { provide: HttpClient, useClass: MockHttpClient }
            ]
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
