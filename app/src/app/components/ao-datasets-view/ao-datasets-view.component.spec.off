import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AoDatasetsViewComponent } from './ao-datasets-view.component';
import { RouterTestingModule } from '@angular/router/testing';
import { MatListModule } from '@angular/material';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { ActivatedRoute } from '@angular/router';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { delay } from 'rxjs/operators';
import { of } from 'rxjs';

class MockAoApiClientService {
    get(url: any) {
        return new Promise((resolve, reject) => {
            resolve({
                data: [
                    {
                        id: 'id1',
                        attributes: {
                            workspace: 'ws1'
                        }
                    },
                    {
                        id: 'id2',
                        attributes: {
                            workspace: 'ws2'
                        }
                    }
                ]
            });
        });
    }
}

class MockActivatedRoute {
    url = of([{ path: 'datasets' }]).pipe(delay(100));
}
class MockGlobalStateStore {
    subscribe(fn: any) {
        setTimeout(fn, 100);
        // call the subscribers async
        return {
            unsubscribe: function () { }
        };
    }

    getProperty() {
        // return fake workspace
        return { id: 'ws1' };
    }

}


describe('AoDatasetsViewComponent', () => {
  let component: AoDatasetsViewComponent;
  let fixture: ComponentFixture<AoDatasetsViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AoDatasetsViewComponent ],
      imports: [RouterTestingModule, MatListModule],
      providers: [
        { provide: AoApiClientService, useClass: MockAoApiClientService },
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        { provide: AoGlobalStateStore, useClass: MockGlobalStateStore }
    ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AoDatasetsViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
