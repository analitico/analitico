import { BrowserModule } from '@angular/platform-browser';
import { NgModule, Injectable, ErrorHandler } from '@angular/core';

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
    MatExpansionModule, MatTableModule, MatSortModule, MatDialog, MatDialogModule, MatProgressBarModule, MatMenuModule, MatTabsModule
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
import { FlexLayoutModule } from '@angular/flex-layout';
import { AoModelViewComponent } from './components/ao-model-view/ao-model-view.component';
import { AoGroupViewComponent } from './components/ao-group-view/ao-group-view.component';
import { DragDropModule } from '@angular/cdk/drag-drop';
import { AoRecipeViewComponent } from './components/ao-recipe-view/ao-recipe-view.component';
import { AoPipelineViewComponent } from './components/ao-pipeline-view/ao-pipeline-view.component';
import { AoEndpointViewComponent } from './components/ao-endpoint-view/ao-endpoint-view.component';
import { AoEndpointPipelinePluginComponent } from './plugins/ao-endpoint-pipeline-plugin/ao-endpoint-pipeline-plugin.component';
import { AoHomeViewComponent } from './components/ao-home-view/ao-home-view.component';
import { AoItemViewComponent } from './components/ao-item-view/ao-item-view.component';
import { AoModelListViewComponent } from './components/ao-model-list-view/ao-model-list-view.component';
import { AoDialogComponent } from './components/ao-dialog/ao-dialog.component';
import { AoItemService } from './services/ao-item/ao-item.service';
import { AoItemBaseViewComponent } from './components/ao-item-base-view/ao-item-base-view.component';

import * as Sentry from '@sentry/browser';
import { AoS24OrderSortingPredictionViewComponent } from './plugins/ao-s24-order-sorting-prediction-view/ao-s24-order-sorting-prediction-view.component';

import { PlotlyModule } from 'angular-plotly.js';
import { CommonModule } from '@angular/common';
import { AoSmartInputBoxComponent } from './components/ao-smart-input-box/ao-smart-input-box.component';
import { AoTransformDataframePluginComponent } from './plugins/ao-transform-dataframe-plugin/ao-transform-dataframe-plugin.component';


Sentry.init({
    dsn: 'https://46fb6b3fc5a14466a97e612c012bf786@sentry.io/1408107'
});

@Injectable()
export class SentryErrorHandler implements ErrorHandler {
    constructor() { }
    handleError(error) {
        Sentry.captureException(error.originalError || error);
        throw error;
    }
}


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
        AoModelViewComponent,
        AoGroupViewComponent,
        AoRecipeViewComponent,
        AoPipelineViewComponent,
        AoEndpointViewComponent,
        AoEndpointPipelinePluginComponent,
        AoHomeViewComponent,
        AoItemViewComponent,
        AoModelListViewComponent,
        AoDialogComponent,
        AoItemBaseViewComponent,
        AoS24OrderSortingPredictionViewComponent,
        AoSmartInputBoxComponent,
        AoTransformDataframePluginComponent
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
        AgGridModule.withComponents([]),
        FlexLayoutModule,
        MatSortModule,
        DragDropModule,
        MatDialogModule,
        MatProgressBarModule,
        MatMenuModule,
        MatTabsModule,
        CommonModule,
        PlotlyModule
    ],
    providers: [{ provide: ErrorHandler, useClass: SentryErrorHandler },
        AoGlobalStateStore, AoApiClientService, AoPluginsService, AoItemService],
    entryComponents: [AoPipelinePluginComponent, AoDataframePipelinePluginComponent,
        AoCsvDataframeSourcePluginComponent, AoRawJsonPluginComponent, AoRecipePipelinePluginComponent,
        AoEndpointPipelinePluginComponent, AoModelListViewComponent, AoDialogComponent, AoItemBaseViewComponent,
        AoS24OrderSortingPredictionViewComponent, AoTransformDataframePluginComponent],
    bootstrap: [AppComponent]
})
export class AppModule {

}
