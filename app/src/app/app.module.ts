import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MainNavComponent } from './components/main-nav/main-nav.component';
import { LayoutModule } from '@angular/cdk/layout';
import { AoLoginComponent } from './components/ao-login/ao-login.component';
import { FormsModule } from '@angular/forms';
import { AoGlobalStateStore } from './services/ao-global-state-store/ao-global-state-store.service';
import { HttpClientModule } from '@angular/common/http';
import { AoApiClientService } from './services/ao-api-client/ao-api-client.service';
import { AoNavListComponent } from './components/ao-nav-list/ao-nav-list.component';
import { AoDatasetViewComponent } from './components/ao-dataset-view/ao-dataset-view.component';
import { AoViewComponent } from './components/ao-view/ao-view.component';
import { AoAnchorDirective } from './directives/ao-anchor/ao-anchor.directive';
import {
    MatSidenavModule, MatToolbarModule, MatIconModule, MatButtonModule, MatListModule,
    MatCardModule, MatInputModule, MatSnackBarModule, MatProgressSpinnerModule
} from '@angular/material';
import { NgJsonEditorModule } from 'ang-jsoneditor';
import { MatFileUploadModule } from 'angular-material-fileupload';
// PLUGINS
import { AoPluginsService } from './services/ao-plugins/ao-plugins.service';
import { AoPipelinePluginComponent } from './plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';
import { AoCsvDataframeSourcePluginComponent } from './plugins/ao-csv-dataframe-source-plugin/ao-csv-dataframe-source-plugin.component';
import { AoRawJsonPluginComponent } from './plugins/ao-raw-json-plugin/ao-raw-json-plugin.component';
import { AoDataframePipelinePluginComponent } from './plugins/ao-dataframe-pipeline-plugin/ao-dataframe-pipeline-plugin.component';
import { AoMatFileUploadComponent } from './components/ao-mat-file-upload/ao-mat-file-upload.component';

@NgModule({
    declarations: [
        AppComponent,
        MainNavComponent,
        AoLoginComponent,
        AoNavListComponent,
        AoDatasetViewComponent,
        AoViewComponent,
        AoAnchorDirective,
        AoPipelinePluginComponent,
        AoCsvDataframeSourcePluginComponent,
        AoRawJsonPluginComponent,
        AoDataframePipelinePluginComponent,
        AoMatFileUploadComponent
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
        MatSnackBarModule,
        FormsModule,
        NgJsonEditorModule,
        MatFileUploadModule,
        MatProgressSpinnerModule
    ],
    providers: [AoGlobalStateStore, AoApiClientService, AoPluginsService],
    entryComponents: [AoPipelinePluginComponent, AoDataframePipelinePluginComponent,
        AoCsvDataframeSourcePluginComponent, AoRawJsonPluginComponent],
    bootstrap: [AppComponent]
})
export class AppModule {

}
