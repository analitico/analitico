import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

import {
    MatSidenavModule, MatToolbarModule, MatIconModule, MatButtonModule, MatListModule,
    MatCardModule, MatInputModule
} from '@angular/material';
import { MainNavComponent } from './components/main-nav/main-nav.component';
import { LayoutModule } from '@angular/cdk/layout';
import { AoLoginComponent } from './components/ao-login/ao-login.component';
import { FormsModule } from '@angular/forms';
import { AoGlobalStateStore } from './services/ao-global-state-store/ao-global-state-store.service';
import { HttpClientModule } from '@angular/common/http';
import { AoApiClientService } from './services/ao-api-client/ao-api-client.service';

@NgModule({
    declarations: [
        AppComponent,
        MainNavComponent,
        AoLoginComponent
    ],
    imports: [
        BrowserModule,
        HttpClientModule,
        AppRoutingModule,
        BrowserAnimationsModule,
        MatSidenavModule,
        MatToolbarModule,
        MatIconModule,
        MatButtonModule,
        LayoutModule,
        MatListModule,
        MatCardModule,
        MatInputModule,
        FormsModule
    ],
    providers: [AoGlobalStateStore, AoApiClientService],
    bootstrap: [AppComponent]
})
export class AppModule { }
