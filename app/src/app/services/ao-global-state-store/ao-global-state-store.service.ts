/**
 * Provides a global state dictionary to share data among components
 * E.g., user profile after login
 */

import { Store } from 'rxjs-observable-store';

class AoGlobalState {
    properties = {};
}

export class AoGlobalStateStore extends Store<AoGlobalState> {
    constructor() {
        super(new AoGlobalState());
    }

    setProperty(propertyName: string, propertyValue: any) {
        const state = this.state;
        state.properties[propertyName] = propertyValue;
        this.setState(state);
    }

    getProperty(propertyName: string) {
        return this.state.properties[propertyName];
    }
}
