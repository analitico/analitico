import { Component, OnDestroy, OnInit } from '@angular/core';
import { AoRefreshable } from './ao-refreshable';
import { Router, NavigationEnd } from '@angular/router';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent implements OnDestroy {
    navigationSubscription: any;
    private routedComponent: AoRefreshable;
    // keep reference of last seen url
    private lastUrl: string = null;

    constructor(private router: Router) {
        this.navigationSubscription = this.router.events.subscribe((e: any) => {
            // If it is a NavigationEnd event re-initalise the component
            // this is done to handle same url navigation case
            if (e instanceof NavigationEnd) {
                // same url -> trigger refresh
                if (this.lastUrl === e.urlAfterRedirects) {
                    console.log('refresh');

                    if (this.routedComponent.refresh) {
                        this.routedComponent.refresh();
                    }
                }
                // save this url
                this.lastUrl = e.urlAfterRedirects;
            }
        });
    }

    setRoutedComponent(component) {
        this.routedComponent = component;
    }

    ngOnDestroy() {
        // remove subscription
        if (this.navigationSubscription) {
            this.navigationSubscription.unsubscribe();
        }
    }
}
