/**
 * Main screen with Material top toolbar and left side navigation
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';


@Component({
    selector: 'app-main-nav',
    templateUrl: './main-nav.component.html',
    styleUrls: ['./main-nav.component.css']
})
export class MainNavComponent implements OnInit, OnDestroy {

    userInitial: string;
    globalStateObserverSubscription: any; // keeps reference of observer subscription for cleanup
    isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
        .pipe(
            map(result => result.matches)
        );

    constructor(private breakpointObserver: BreakpointObserver, private globalState: AoGlobalStateStore) { }

    ngOnInit() {
        this.userInitial = null;
        const that = this;
        this.globalStateObserverSubscription = this.globalState.subscribe(this.onGlobalStateUpdate.bind(this));
    }

    ngOnDestroy() {
        // unsubscribe to avoid memory leaks
        this.globalStateObserverSubscription.unsubscribe();
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
    }
}
