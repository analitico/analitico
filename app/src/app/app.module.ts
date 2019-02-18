import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MainNavComponent } from './components/main-nav/main-nav.component';
import { LayoutModule } from '@angular/cdk/layout';
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
    MatCardModule, MatInputModule, MatSnackBarModule, MatProgressSpinnerModule, MatSelectModule, MatOptionModule,
    MatExpansionModule, MatTableModule, MatPaginatorModule, MatGridListModule
} from '@angular/material';
import { NgJsonEditorModule } from 'ang-jsoneditor';
// PLUGINS
import { AoPluginsService } from './services/ao-plugins/ao-plugins.service';
import { AoPipelinePluginComponent } from './plugins/ao-pipeline-plugin/ao-pipeline-plugin.component';
import { AoCsvDataframeSourcePluginComponent } from './plugins/ao-csv-dataframe-source-plugin/ao-csv-dataframe-source-plugin.component';
import { AoRawJsonPluginComponent } from './plugins/ao-raw-json-plugin/ao-raw-json-plugin.component';
import { AoDataframePipelinePluginComponent } from './plugins/ao-dataframe-pipeline-plugin/ao-dataframe-pipeline-plugin.component';
import { AoMatFileUploadComponent } from './components/ao-mat-file-upload/ao-mat-file-upload.component';
import { AoMatFileUploadQueueComponent } from './components/ao-mat-file-upload-queue/ao-mat-file-upload-queue.component';
import { AoFileUploadInputForDirective } from './directives/ao-file-upload-input-for/ao-file-upload-input-for.directive';
import { AoNavListFromUrlComponent } from './components/ao-nav-list-from-url/ao-nav-list-from-url.component';
import { AoRecipePipelinePluginComponent } from './plugins/ao-recipe-pipeline-plugin/ao-recipe-pipeline-plugin.component';
import { AoTableViewComponent } from './components/ao-table-view/ao-table-view.component';
import { AgGridModule } from 'ag-grid-angular';
import { AoDatasetsViewComponent } from './components/ao-datasets-view/ao-datasets-view.component';
import { AoGroupWsViewComponent } from './components/ao-group-ws-view/ao-group-ws-view.component';
import { AoModelsViewComponent } from './components/ao-models-view/ao-models-view.component';


@NgModule({
    declarations: [
        AppComponent,
        MainNavComponent,
        AoNavListComponent,
        AoDatasetViewComponent,
        AoViewComponent,
        AoAnchorDirective,
        AoPipelinePluginComponent,
        AoCsvDataframeSourcePluginComponent,
        AoRawJsonPluginComponent,
        AoDataframePipelinePluginComponent,
        AoMatFileUploadComponent,
        AoMatFileUploadQueueComponent,
        AoFileUploadInputForDirective,
        AoNavListFromUrlComponent,
        AoRecipePipelinePluginComponent,
        AoTableViewComponent,
        AoDatasetsViewComponent,
        AoGroupWsViewComponent,
        AoModelsViewComponent,

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
        MatProgressSpinnerModule,
        MatSelectModule,
        MatOptionModule,
        MatExpansionModule,
        MatTableModule,
        MatPaginatorModule,
        AgGridModule.withComponents([]),
        MatGridListModule
    ],
    providers: [AoGlobalStateStore, AoApiClientService, AoPluginsService],
    entryComponents: [AoPipelinePluginComponent, AoDataframePipelinePluginComponent,
        AoCsvDataframeSourcePluginComponent, AoRawJsonPluginComponent, AoRecipePipelinePluginComponent],
    bootstrap: [AppComponent]
})
export class AppModule {

}
