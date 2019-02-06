/**
 * Main screen with Material top toolbar and left side navigation
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    selector: 'app-main-nav',
    templateUrl: './main-nav.component.html',
    styleUrls: ['./main-nav.component.css']
})
export class MainNavComponent implements OnInit, OnDestroy {

    userInitial: string;
    userBadgeIconUrl: string;
    globalStateObserverSubscription: any; // keeps reference of observer subscription for cleanup
    datasetsFilter: any;
    workspaces: any;
    datasetTitle: string;

    isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
        .pipe(
            map(result => result.matches)
        );

    constructor(private breakpointObserver: BreakpointObserver, private globalState: AoGlobalStateStore,
        private apiClient: AoApiClientService) { }

    ngOnInit() {
        this.userInitial = null;
        const that = this;
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
        // load workspaces
        this.loadWorkspaces();

    }

    loadWorkspaces() {
        this.apiClient.get('/workspaces')
            .then((response: any) => {
                this.workspaces = response.data;
                if (this.workspaces.length > 0) {
                    // pick up first workspace
                    let workspace = this.workspaces[0];
                    this.workspaces.forEach(w => {
                        // if we have ws_test workspace, select this (for testing)
                        if (w.id === 'ws_test') {
                            workspace = w;
                            return false;
                        }
                    });
                    // set workspace
                    this.globalState.setProperty('workspace', workspace.id);
                }
            });
    }

    ngOnDestroy() {
        // unsubscribe to avoid memory leaks
        if (this.globalStateObserverSubscription) {
            this.globalStateObserverSubscription.unsubscribe();
        }
    }

    onGlobalStateUpdate() {
        // retrieve user
        const user = this.globalState.getProperty('user');
        if (user && user.username) {
            // set firstname initial into badge at top right
            this.userInitial = user.username[0].toUpperCase();
        } else {
            this.userInitial = null;
        }
        // if we have a workspace we want to notify it
        const workspace = this.globalState.getProperty('workspace');
        if (workspace) {
            this.changeWorkspace(workspace);
        }
    }

    changeWorkspace(workspaceId: string) {
        // add a filter to the dataset list
        this.datasetsFilter = { 'attributes.workspace': workspaceId };
    }

    // create a new dataset
    createDataset() {
        const workspace = this.globalState.getProperty('workspace');
        const params = { 'workspace': workspace, attributes: {}};
        if (this.datasetTitle) {
            params.attributes['title'] = this.datasetTitle;
        }
        this.apiClient.post('/datasets', params)
            .then((response: any) => {
                // refresh dataset list
                this.changeWorkspace(workspace);
            });
    }
}
