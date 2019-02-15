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
    workspaceFilter: any;
    workspaces: any;
    workspace: any;
    selectedWorkspace: any;
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
                        if (w.id === 'ws_s24') {
                            workspace = w;
                            return false;
                        }
                    });
                    // set workspace
                    this.globalState.setProperty('workspace', workspace);
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

        const workspace = this.globalState.getProperty('workspace');
        // if the workspace is changed
        if (this.workspace !== workspace) {
            // update
            this.selectedWorkspace = workspace;
            this.workspace = workspace;
            this.setWorkspacefilter();
        }
    }

    // called by select input control
    changedWorkspace() {
        // set new workspace
        this.globalState.setProperty('workspace', this.selectedWorkspace);
    }

    // set a filter for children components (datasets/recipes/models/etc...)
    setWorkspacefilter() {
        this.workspaceFilter = { 'attributes.workspace': this.workspace.id };
    }

    // create a new dataset
    createDataset() {
        const workspace = this.globalState.getProperty('workspace');
        const params = { 'workspace': workspace.id, attributes: {} };
        if (this.datasetTitle) {
            params.attributes['title'] = this.datasetTitle;
        }
        this.apiClient.post('/datasets', params)
            .then((response: any) => {
                // refresh all components
                this.setWorkspacefilter();
            });
    }

    // define default sort function on created_at attributes
    sortByCreatedAtDescFunction = function (a, b) {
        try {
            if (!a.attributes || !b.attributes || !a.attributes.created_at || !b.attributes.created_at) {
                return -1;
            }
            return a.attributes.created_at > b.attributes.created_at ? -1 : 1;
        } catch (e) {
            console.error(e);
        }
    };
}
