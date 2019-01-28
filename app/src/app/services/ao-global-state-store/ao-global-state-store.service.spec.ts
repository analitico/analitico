import { TestBed } from '@angular/core/testing';

import { AoGlobalStateStore } from './ao-global-state-store.service';

describe('AoGlobalStateStore', () => {
    let store: AoGlobalStateStore;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [AoGlobalStateStore]
        });

        store = new AoGlobalStateStore();
    });

    it('should correctly update the state when calling setState', () => {
        store.setProperty('user', { email: 'test@analitico.ai' });
        expect(store.getProperty('user')).toEqual({ email: 'test@analitico.ai' });
    });

    it('should push updated state to subscribers', done => {
        store.setProperty('user', { email: 'test@analitico.ai' });
        store.state$.subscribe(state => {
            expect(state.properties['user']).toEqual({ email: 'test@analitico.ai' });
            done();
        });
    });

});
