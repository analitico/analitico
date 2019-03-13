/**
 * Main screen with Material top toolbar and left side navigation
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, take } from 'rxjs/operators';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';
import { setDefaultService } from 'selenium-webdriver/edge';
import { Router, ActivatedRoute } from '@angular/router';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-main-nav',
    templateUrl: './main-nav.component.html',
    styleUrls: ['./main-nav.component.css']
})
export class MainNavComponent implements OnInit, OnDestroy {

    userInitial: string;
    userPhotoUrl: string;
    userBadgeIconUrl: string;
    globalStateObserverSubscription: any; // keeps reference of observer subscription for cleanup
    workspaceFilter: any;
    workspaces: any;
    workspace: any;
    selectedWorkspace: any;
    datasetTitle: string;
    newItemParams: any;
    initialized = false;
    // bound to the search text box
    searchQueryInput: string;
    queryParamsSubscription: any;
    query: string;
    user: any;

    isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
        .pipe(
            map(result => result.matches)
        );

    constructor(private breakpointObserver: BreakpointObserver, private globalState: AoGlobalStateStore,
        private apiClient: AoApiClientService, protected router: Router, protected route: ActivatedRoute,
        protected itemService: AoItemService) { }

    ngOnInit() {
        this.userInitial = null;
        const that = this;
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
        // subscribe to query parameters subscription
        this.queryParamsSubscription = this.route.queryParams.subscribe(params => {

            this.searchQueryInput = params.q;

        });
        // check user logged
        this.getUser()
            .then(() => {
                this.initialized = true;
                // load workspaces
                return this.loadWorkspaces();
            })
            .then(() => {
                const lastWorkspaceId = localStorage.getItem('workspaceId');
                if (lastWorkspaceId) {
                    const lastWorkspace = this.getWorkspaceById(lastWorkspaceId);
                    if (lastWorkspace) {
                        // set last workspace
                        return this.setWorkspace(lastWorkspace);
                    }
                }
                if (this.workspaces.length > 0) {
                    // set first workspace
                    this.setWorkspace(this.workspaces[0]);
                }
            });

    }

    ngOnDestroy() {
        // unsubscribe to avoid memory leaks
        if (this.globalStateObserverSubscription) {
            this.globalStateObserverSubscription.unsubscribe();
        }
        if (this.queryParamsSubscription) {
            this.queryParamsSubscription.unsubscribe();
        }
    }


    loadWorkspaces() {
        return this.apiClient.get('/workspaces')
            .then((response: any) => {
                this.workspaces = response.data;
            });
    }

    getWorkspaceById(workspaceId) {
        for (let i = 0; i < this.workspaces.length; i++) {
            if (this.workspaces[i].id === workspaceId) {
                return this.workspaces[i];
            }
        }
        return false;
    }

    // called by select input control
    changedWorkspace() {
        // set new workspace
        this.setWorkspace(this.selectedWorkspace);
    }

    setWorkspace(workspace) {
        // set workspace
        this.globalState.setProperty('workspace', workspace);
        // save id
        localStorage.setItem('workspaceId', workspace.id);
    }



    onGlobalStateUpdate() {
        // retrieve user
        const user = this.globalState.getProperty('user');
        this.user = user;
        this.userInitial = null;
        if (user) {
            if (user.attributes.photos && user.attributes.photos.length > 0) {
                this.userPhotoUrl = user.attributes.photos[0].value;
            } else if (user.attributes.first_name) {
                // set firstname initial into badge at top right
                this.userInitial = user.attributes.first_name[0].toUpperCase();
            }

        }

        const workspace = this.globalState.getProperty('workspace');
        // if the workspace is changed
        if (this.workspace !== workspace) {
            // update
            this.selectedWorkspace = workspace;
            this.workspace = workspace;
            // set params for creating new items
            this.newItemParams = { workspace_id: workspace.id };
            this.setWorkspacefilter();
        }
    }



    // set a filter for children components (datasets/recipes/models/etc...)
    setWorkspacefilter() {
        this.workspaceFilter = { 'attributes.workspace_id': this.workspace.id };
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

    getUser() {
        return this.apiClient.get('/users/me')
            .then((response: any) => {
                // notify new user
                this.globalState.setProperty('user', response.data);
            })
            .catch((response: any) => {

                // redirect to login
                window.location.href = '/accounts/login/';

            });
    }

    // perform a search into the workspace
    search() {
        let queryParams = {};

        queryParams = { q: this.searchQueryInput };

        this.router.navigate([], { queryParams: queryParams, relativeTo: this.route, queryParamsHandling: 'merge' });
    }

    logout() {
        location.href = '/accounts/logout/';
    }

}
