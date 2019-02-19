import { LayoutModule } from '@angular/cdk/layout';
import { async, ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatSidenavModule,
    MatToolbarModule,
    MatSelectModule,
    MatOptionModule,
    MatExpansionModule
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
            let response = {};
            if (url === '/workspaces') {
                response = {
                    data: [{
                        id: 'ws1',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    },
                    {
                        id: 'ws2',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    }]
                };
            } else if (url === '/datasets') {
                response = {
                    data: [{
                        id: 'ds1',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    },
                    {
                        id: 'ds2',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    }]
                };
            } else if (url === '/recipes') {
                response = {
                    data: [{
                        id: 'rx1',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    },
                    {
                        id: 'rx2',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    }]
                };
            } else if (url === '/models') {
                response = {
                    data: [{
                        id: 'ml1',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    },
                    {
                        id: 'ml2',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    }]
                };
            } else if (url === '/endpoints') {
                response = {
                    data: [{
                        id: 'ep1',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    },
                    {
                        id: 'ep2',
                        attributes: {
                            created_at: '2019-02-07T20:37:29.057283+01:00'
                        }
                    }]
                };
            }
            resolve(response);
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
                RouterTestingModule,
                MatSelectModule,
                MatOptionModule,
                MatExpansionModule
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

    it('should load first workspace', async(() => {
        fixture.whenStable().then(() => {
            fixture.detectChanges();
            expect(component.workspace.id).toEqual('ws1');
        });
    }));

    it('should change workspace', async(() => {
        fixture.whenStable().then(() => {
            fixture.detectChanges();
            expect(component.workspace.id).toEqual('ws1');
            component.selectedWorkspace = { id: 'ws2' };
            fixture.whenStable().then(() => {
                fixture.detectChanges();
                expect(component.workspace.id).toEqual('ws2');
                expect(component.workspaceFilter['attributes.workspace_id']).toEqual('ws2');
            });
            component.changedWorkspace();
        });
    }));
});
