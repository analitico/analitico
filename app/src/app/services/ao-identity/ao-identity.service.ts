/**
 * It contains all methods to do authentication
 */

import { AoGlobalStateStore } from '../ao-global-state-store/ao-global-state-store.service';
import { AoApiClientService } from '../ao-api-client/ao-api-client.service';
import { Injectable } from '@angular/core';

@Injectable({
    providedIn: 'root',
})

export class AoIdentityService {

    constructor(private globalState: AoGlobalStateStore, private apiClient: AoApiClientService) { }

    /**
     * Load current user profile and notify to global state
     */
    getUserProfile(): void {
        this.apiClient.get('/profile')
        .then((response: any) => {
            // notify to global state the user profile
            this.globalState.setProperty('user', response.data);
        })
        .catch((error: any) => {
        });
    }
}
