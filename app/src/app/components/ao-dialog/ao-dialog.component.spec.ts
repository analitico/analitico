import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoDialogComponent } from './ao-dialog.component';
import { MatCardModule, MatToolbarModule, MatButtonModule } from '@angular/material';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';

describe('AoDialogComponent', () => {
    let component: AoDialogComponent;
    let fixture: ComponentFixture<AoDialogComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [AoDialogComponent],
            providers: [MatDialogRef],
            imports: [MatCardModule, MatToolbarModule, MatButtonModule, MatDialogModule]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AoDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
