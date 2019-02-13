import { LayoutModule } from '@angular/cdk/layout';
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatSidenavModule,
    MatToolbarModule
} from '@angular/material';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { MainNavComponent } from './main-nav.component';
import { AoNavListFromUrlComponent } from 'src/app/components/ao-nav-list-from-url/ao-nav-list-from-url.component';
import { FormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: {
                    id: '1',
                    attributes: {
                        'plugin': {
                            'type': 'analitico/plugin',
                            'name': 'analitico.plugin.CsvDataframeSourcePlugin'
                        }
                    }
                }
            });
        });

    }
}


describe('MainNavComponent', () => {
    let component: MainNavComponent;
    let fixture: ComponentFixture<MainNavComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [MainNavComponent, AoNavListFromUrlComponent],
            imports: [
                NoopAnimationsModule,
                LayoutModule,
                MatButtonModule,
                MatIconModule,
                MatListModule,
                MatSidenavModule,
                MatToolbarModule,
                FormsModule,
                RouterTestingModule
            ],
            providers: [AoGlobalStateStore, { provide: AoApiClientService, useClass: MockAoApiClientService }]
        }).compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(MainNavComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should compile', () => {
        expect(component).toBeTruthy();
    });
});
